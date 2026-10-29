"""
api.py - FastAPI service for House Price Prediction and MongoDB persistence.
Endpoints:
- POST /predict: Predicts price from 5 input groups, saves to properties and predictions collections
- GET /predictions: Retrieves latest N predictions
- GET /properties/{id}: Retrieves stored property details
- GET /metrics: Returns model evaluation metrics from reports/metrics.json
- GET /health: Health check status
- GET /: Serves minimal single-page web UI
"""

import os
import sys
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import joblib

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.features import HousePricePipeline, SEATTLE_LAT, SEATTLE_LONG
from src.db import get_database, insert_property, get_property, insert_prediction, get_predictions

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="King County House Price Prediction API",
    description="Production-grade ML API estimating residential property prices with MongoDB persistence",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model and metadata references
MODEL_PIPELINE: Optional[HousePricePipeline] = None
MODEL_METADATA: Dict[str, Any] = {}
ZIPCODE_GEO_MAP: Dict[str, Dict[str, float]] = {}


def load_artifacts():
    global MODEL_PIPELINE, MODEL_METADATA, ZIPCODE_GEO_MAP
    model_path = "models/best_model.joblib"
    meta_path = "models/model_metadata.json"

    if os.path.exists(model_path):
        MODEL_PIPELINE = joblib.load(model_path)
        logger.info(f"Loaded production model from {model_path}")
    else:
        logger.warning(f"Model file {model_path} not found. Train model before calling /predict.")

    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            MODEL_METADATA = json.load(f)

    # Build zipcode centroid cache for coordinate imputation
    clean_csv = "data/processed/kc_house_data_clean.csv"
    if os.path.exists(clean_csv):
        df_geo = pd.read_csv(clean_csv, usecols=['zipcode', 'lat', 'long'])
        df_geo['zipcode'] = df_geo['zipcode'].astype(str)
        grouped = df_geo.groupby('zipcode')[['lat', 'long']].median()
        ZIPCODE_GEO_MAP = grouped.to_dict(orient='index')


# Pydantic Schemas for 5 Input Groups
class AreaInput(BaseModel):
    sqft_living: float = Field(..., gt=100, lt=20000, description="Interior living space in sqft", examples=[2100.0])
    sqft_lot: float = Field(..., gt=200, lt=2000000, description="Lot size in sqft", examples=[6500.0])
    sqft_above: Optional[float] = Field(None, ge=0, description="Finished space above ground in sqft", examples=[1600.0])
    sqft_basement: Optional[float] = Field(0.0, ge=0, description="Basement space in sqft", examples=[500.0])


class BedroomsInput(BaseModel):
    bedrooms: float = Field(..., ge=1, le=12, description="Number of bedrooms (1-12)", examples=[3.0])
    bathrooms: float = Field(..., ge=0.5, le=10, description="Number of bathrooms (0.5-10)", examples=[2.25])
    floors: float = Field(1.0, ge=1.0, le=4.0, description="Number of floors (1-4)", examples=[1.5])


class LocationInput(BaseModel):
    zipcode: str = Field(..., description="5-digit King County zipcode", examples=["98103"])
    lat: Optional[float] = Field(None, ge=47.0, le=48.0, description="Latitude (auto-filled if omitted)")
    long: Optional[float] = Field(None, ge=-123.0, le=-121.0, description="Longitude (auto-filled if omitted)")


class PropertyAgeInput(BaseModel):
    yr_built: int = Field(..., ge=1900, le=2026, description="Year the property was constructed", examples=[1978])
    yr_renovated: Optional[int] = Field(0, ge=0, le=2026, description="Year renovated (0 if never renovated)", examples=[0])
    sale_year: Optional[int] = Field(2015, ge=2014, le=2026, description="Transaction reference year", examples=[2015])


class AmenitiesInput(BaseModel):
    waterfront: int = Field(0, ge=0, le=1, description="Waterfront property flag (0: No, 1: Yes)", examples=[0])
    view: int = Field(0, ge=0, le=4, description="View quality rating (0: None, 4: Excellent)", examples=[0])
    condition: int = Field(3, ge=1, le=5, description="Overall condition (1: Poor, 5: Pristine)", examples=[3])
    grade: int = Field(7, ge=1, le=13, description="King County construction grade (1: Substandard, 13: Mansion)", examples=[7])


class PropertyPredictionRequest(BaseModel):
    property_id: Optional[str] = Field(None, description="Optional custom property identifier")
    area: AreaInput
    bedrooms: BedroomsInput
    location: LocationInput
    property_age: PropertyAgeInput
    amenities: AmenitiesInput
    actual_price: Optional[float] = Field(None, ge=0, description="Optional actual historical price for comparison")


class PredictionResponse(BaseModel):
    property_id: str
    predicted_price: float
    formatted_price: str
    model_name: str
    model_version: str
    amenity_score: float
    distance_to_seattle_miles: float
    stored_in_db: bool
    predicted_at: str


@app.on_event("startup")
def on_startup():
    load_artifacts()


@app.get("/health", tags=["System"])
def health_check():
    """Health status and service availability."""
    db_ok = False
    try:
        db = get_database()
        db.command('ping')
        db_ok = True
    except Exception as e:
        logger.warning(f"Database ping failed: {e}")

    return {
        "status": "healthy" if (MODEL_PIPELINE is not None and db_ok) else "degraded",
        "model_loaded": MODEL_PIPELINE is not None,
        "database_connected": db_ok,
        "model_version": MODEL_METADATA.get("version", "1.0.0"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/metrics", tags=["Evaluation"])
def get_model_metrics():
    """Returns cross-validation and test evaluation metrics."""
    metrics_path = "reports/metrics.json"
    if not os.path.exists(metrics_path):
        raise HTTPException(status_code=404, detail="Metrics file not found. Run model training first.")
    with open(metrics_path, 'r') as f:
        data = json.load(f)
    return data


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
def predict_price(req: PropertyPredictionRequest):
    """
    Accepts 5 input groups, validates schema, runs model inference,
    and records documents to MongoDB 'properties' and 'predictions'.
    """
    if MODEL_PIPELINE is None:
        load_artifacts()
        if MODEL_PIPELINE is None:
            raise HTTPException(status_code=503, detail="Model is not loaded. Please train the model first.")

    # 1. Resolve coordinates if not provided
    zipcode_clean = str(req.location.zipcode).strip()
    lat = req.location.lat
    long_ = req.location.long

    if (lat is None or long_ is None) and zipcode_clean in ZIPCODE_GEO_MAP:
        centroid = ZIPCODE_GEO_MAP[zipcode_clean]
        lat = lat or centroid['lat']
        long_ = long_ or centroid['long']

    # Fallback to Seattle downtown coordinates if unknown
    lat = lat if lat is not None else SEATTLE_LAT
    long_ = long_ if long_ is not None else SEATTLE_LONG

    # 2. Resolve sqft_above / basement
    sqft_living = req.area.sqft_living
    sqft_basement = req.area.sqft_basement or 0.0
    sqft_above = req.area.sqft_above if req.area.sqft_above is not None else max(sqft_living - sqft_basement, 0.0)

    # 3. Construct input DataFrame row
    row_dict = {
        'sqft_living': sqft_living,
        'sqft_lot': req.area.sqft_lot,
        'sqft_above': sqft_above,
        'sqft_basement': sqft_basement,
        'bedrooms': req.bedrooms.bedrooms,
        'bathrooms': req.bedrooms.bathrooms,
        'floors': req.bedrooms.floors,
        'zipcode': zipcode_clean,
        'lat': lat,
        'long': long_,
        'yr_built': req.property_age.yr_built,
        'yr_renovated': req.property_age.yr_renovated or 0,
        'sale_year': req.property_age.sale_year or 2015,
        'waterfront': req.amenities.waterfront,
        'view': req.amenities.view,
        'condition': req.amenities.condition,
        'grade': req.amenities.grade
    }

    df_in = pd.DataFrame([row_dict])

    # 4. Predict Price
    try:
        pred_arr = MODEL_PIPELINE.predict(df_in)
        predicted_price = float(pred_arr[0])
    except Exception as e:
        logger.error(f"Inference error: {e}")
        raise HTTPException(status_code=500, detail=f"Model inference failed: {str(e)}")

    # 5. Extract engineered metrics for response
    transformed = MODEL_PIPELINE.transform(df_in)
    amenity_score = float(transformed['amenity_score'].iloc[0])
    dist_seattle = float(transformed['distance_to_seattle'].iloc[0])

    # 6. MongoDB Persistence
    property_id = req.property_id or f"prop_{uuid.uuid4().hex[:10]}"
    now_utc = datetime.now(timezone.utc)
    stored_in_db = False

    try:
        db = get_database()
        # Insert or update property document
        property_doc = {
            "property_id": property_id,
            "area_sqft": sqft_living,
            "lot_sqft": req.area.sqft_lot,
            "sqft_above": sqft_above,
            "sqft_basement": sqft_basement,
            "bedrooms": req.bedrooms.bedrooms,
            "bathrooms": req.bedrooms.bathrooms,
            "floors": req.bedrooms.floors,
            "location": {
                "zipcode": zipcode_clean,
                "lat": lat,
                "long": long_
            },
            "age_years": max(req.property_age.sale_year - req.property_age.yr_built, 0),
            "yr_built": req.property_age.yr_built,
            "yr_renovated": req.property_age.yr_renovated or 0,
            "renovated": bool(req.property_age.yr_renovated and req.property_age.yr_renovated > 0),
            "amenities": {
                "waterfront": req.amenities.waterfront,
                "view": req.amenities.view,
                "condition": req.amenities.condition,
                "grade": req.amenities.grade
            },
            "actual_price": req.actual_price,
            "created_at": now_utc
        }
        insert_property(property_doc, db)

        # Insert prediction document
        prediction_doc = {
            "property_id": property_id,
            "model_name": "Random Forest Regressor",
            "model_version": MODEL_METADATA.get("version", "1.0.0"),
            "predicted_price": round(predicted_price, 2),
            "input_snapshot": req.model_dump(),
            "predicted_at": now_utc
        }
        insert_prediction(prediction_doc, db)
        stored_in_db = True
    except Exception as e:
        logger.error(f"Failed to persist prediction to MongoDB: {e}")

    return PredictionResponse(
        property_id=property_id,
        predicted_price=round(predicted_price, 2),
        formatted_price=f"${predicted_price:,.2f}",
        model_name="Random Forest Regressor",
        model_version=MODEL_METADATA.get("version", "1.0.0"),
        amenity_score=round(amenity_score, 2),
        distance_to_seattle_miles=round(dist_seattle, 2),
        stored_in_db=stored_in_db,
        predicted_at=now_utc.isoformat()
    )


@app.get("/predictions", tags=["Persistence"])
def list_predictions(limit: int = Query(20, ge=1, le=100)):
    """Retrieves recent predictions stored in MongoDB."""
    try:
        db = get_database()
        preds = get_predictions(limit=limit, db=db)
        # Convert datetime objects to string
        for p in preds:
            if isinstance(p.get("predicted_at"), datetime):
                p["predicted_at"] = p["predicted_at"].isoformat()
        return preds
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@app.get("/properties/{property_id}", tags=["Persistence"])
def retrieve_property(property_id: str):
    """Retrieves stored property details by property_id."""
    try:
        db = get_database()
        prop = get_property(property_id, db=db)
        if not prop:
            raise HTTPException(status_code=404, detail=f"Property {property_id} not found.")
        if isinstance(prop.get("created_at"), datetime):
            prop["created_at"] = prop["created_at"].isoformat()
        return prop
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")


@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def serve_frontend():
    """Serves minimal, modern single-page dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>King County House Price Predictor</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --border: #334155;
      --success: #10b981;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); padding: 24px; }
    .container { max-width: 1100px; margin: 0 auto; }
    header { text-align: center; margin-bottom: 28px; }
    header h1 { font-size: 2rem; color: #fff; margin-bottom: 8px; }
    header p { color: var(--text-muted); font-size: 0.95rem; }
    .badge { display: inline-block; background: #0369a1; color: #e0f2fe; padding: 3px 10px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
    @media (max-width: 850px) { .grid { grid-template-columns: 1fr; } }
    .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 24px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4); }
    .card h2 { font-size: 1.2rem; color: var(--accent); margin-bottom: 16px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
    .section-title { font-size: 0.85rem; font-weight: 700; color: var(--accent); text-transform: uppercase; margin-top: 14px; margin-bottom: 6px; letter-spacing: 0.05em; }
    .form-group { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 8px; }
    label { display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 4px; }
    input, select { width: 100%; padding: 8px 12px; background: #0f172a; border: 1px solid var(--border); border-radius: 6px; color: #fff; font-size: 0.9rem; }
    input:focus, select:focus { outline: none; border-color: var(--accent); }
    .btn-row { display: flex; gap: 10px; margin-top: 18px; }
    button { flex: 1; padding: 12px; background: var(--accent); color: #0f172a; border: none; border-radius: 6px; font-weight: 700; cursor: pointer; transition: all 0.2s; font-size: 0.95rem; }
    button:hover { background: var(--accent-hover); }
    button.btn-sec { background: transparent; color: var(--text-muted); border: 1px solid var(--border); }
    button.btn-sec:hover { background: #334155; color: #fff; }
    .result-box { margin-top: 20px; padding: 18px; border-radius: 8px; background: #0f172a; border: 1px solid var(--border); text-align: center; }
    .price-display { font-size: 2.2rem; font-weight: 800; color: var(--success); margin: 6px 0; }
    .meta-tag { display: inline-block; font-size: 0.8rem; color: var(--text-muted); background: #1e293b; padding: 3px 8px; border-radius: 4px; margin: 2px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin-top: 12px; }
    th, td { text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--border); }
    th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }
    .table-container { max-height: 400px; overflow-y: auto; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <span class="badge">Machine Learning &bull; MongoDB &bull; FastAPI</span>
      <h1>King County House Price Predictor</h1>
      <p>Estimate property prices using 5 core housing dimensions calibrated on King County real estate sales</p>
    </header>

    <div class="grid">
      <!-- Input Form Card -->
      <div class="card">
        <h2>Property Specifications</h2>
        <form id="predictForm">
          <div class="section-title">1. Area Dimensions</div>
          <div class="form-group">
            <div>
              <label>Living Area (sqft)</label>
              <input type="number" id="sqft_living" value="2150" required>
            </div>
            <div>
              <label>Lot Size (sqft)</label>
              <input type="number" id="sqft_lot" value="6500" required>
            </div>
          </div>
          <div class="form-group">
            <div>
              <label>Above Ground (sqft)</label>
              <input type="number" id="sqft_above" value="1650">
            </div>
            <div>
              <label>Basement (sqft)</label>
              <input type="number" id="sqft_basement" value="500">
            </div>
          </div>

          <div class="section-title">2. Bedrooms & Bathrooms</div>
          <div class="form-group">
            <div>
              <label>Bedrooms</label>
              <input type="number" id="bedrooms" value="3" min="1" max="10" required>
            </div>
            <div>
              <label>Bathrooms</label>
              <input type="number" id="bathrooms" step="0.25" value="2.25" required>
            </div>
          </div>
          <div class="form-group">
            <div>
              <label>Floors</label>
              <input type="number" id="floors" step="0.5" value="1.5" required>
            </div>
            <div>
              <label>Optional Property ID</label>
              <input type="text" id="prop_id" placeholder="Auto-generated">
            </div>
          </div>

          <div class="section-title">3. Location</div>
          <div class="form-group">
            <div>
              <label>Zipcode</label>
              <input type="text" id="zipcode" value="98103" required>
            </div>
            <div>
              <label>City / Area Reference</label>
              <select id="presetLocation" onchange="applyPreset(this.value)">
                <option value="seattle_greenlake">Seattle (Green Lake - 98103)</option>
                <option value="bellevue_luxury">Bellevue (Luxury - 98004)</option>
                <option value="redmond_tech">Redmond (Tech Hub - 98052)</option>
                <option value="renton_suburb">Renton (South County - 98055)</option>
              </select>
            </div>
          </div>

          <div class="section-title">4. Property Age & Renovation</div>
          <div class="form-group">
            <div>
              <label>Year Built</label>
              <input type="number" id="yr_built" value="1982" required>
            </div>
            <div>
              <label>Year Renovated (0 if none)</label>
              <input type="number" id="yr_renovated" value="0">
            </div>
          </div>

          <div class="section-title">5. Amenities & Construction Grade</div>
          <div class="form-group">
            <div>
              <label>Waterfront</label>
              <select id="waterfront">
                <option value="0">No (0)</option>
                <option value="1">Yes (1)</option>
              </select>
            </div>
            <div>
              <label>View Quality (0-4)</label>
              <select id="view">
                <option value="0">0 - None</option>
                <option value="1">1 - Fair</option>
                <option value="2">2 - Average</option>
                <option value="3">3 - Good</option>
                <option value="4">4 - Excellent</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <div>
              <label>Condition (1-5)</label>
              <select id="condition">
                <option value="1">1 - Poor</option>
                <option value="2">2 - Fair</option>
                <option value="3" selected>3 - Average</option>
                <option value="4">4 - Good</option>
                <option value="5">5 - Very Good</option>
              </select>
            </div>
            <div>
              <label>King County Grade (1-13)</label>
              <select id="grade">
                <option value="5">5 - Low</option>
                <option value="6">6 - Low Average</option>
                <option value="7">7 - Average</option>
                <option value="8" selected>8 - Good</option>
                <option value="9">9 - Better</option>
                <option value="10">10 - Very Good</option>
                <option value="11">11 - Excellent</option>
                <option value="12">12 - Luxury</option>
                <option value="13">13 - Mansion</option>
              </select>
            </div>
          </div>

          <div class="btn-row">
            <button type="submit" id="btnSubmit">Calculate Estimated Value</button>
            <button type="button" class="btn-sec" onclick="resetForm()">Reset</button>
          </div>
        </form>

        <div id="resultBox" class="resultBox" style="display: none;">
          <div style="font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase;">Estimated Market Valuation</div>
          <div class="price-display" id="resPrice">$0</div>
          <div>
            <span class="meta-tag" id="resModel">Random Forest</span>
            <span class="meta-tag" id="resDistance">Dist: 0 mi</span>
            <span class="meta-tag" id="resAmenity">Amenity: 0.0</span>
            <span class="meta-tag" id="resSaved" style="color: var(--success);">Saved to Mongo</span>
          </div>
        </div>
      </div>

      <!-- Right Column: Recent Predictions Table & DB History -->
      <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px;">
          <h2 style="border: none; margin: 0; padding: 0;">MongoDB Audit Log</h2>
          <button class="btn-sec" style="padding: 4px 10px; font-size: 0.75rem;" onclick="fetchHistory()">Refresh</button>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px;">Real-time feed of prediction documents persisted in MongoDB collection <code>predictions</code>.</p>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Property ID</th>
                <th>Zipcode</th>
                <th>Specs</th>
                <th>Valuation</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody id="historyBody">
              <tr><td colspan="5" style="text-align: center; color: var(--text-muted);">Loading predictions...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <script>
    const PRESETS = {
      seattle_greenlake: { living: 2150, lot: 5000, beds: 3, baths: 2.0, floors: 1.5, zip: '98103', yr: 1948, grade: 8, view: 0 },
      bellevue_luxury: { living: 4200, lot: 12000, beds: 5, baths: 4.5, floors: 2.0, zip: '98004', yr: 2008, grade: 11, view: 2 },
      redmond_tech: { living: 2800, lot: 7500, beds: 4, baths: 2.5, floors: 2.0, zip: '98052', yr: 1996, grade: 9, view: 0 },
      renton_suburb: { living: 1650, lot: 6200, beds: 3, baths: 1.75, floors: 1.0, zip: '98055', yr: 1974, grade: 7, view: 0 }
    };

    function applyPreset(key) {
      const p = PRESETS[key];
      if (!p) return;
      document.getElementById('sqft_living').value = p.living;
      document.getElementById('sqft_lot').value = p.lot;
      document.getElementById('sqft_above').value = p.living - 400;
      document.getElementById('sqft_basement').value = 400;
      document.getElementById('bedrooms').value = p.beds;
      document.getElementById('bathrooms').value = p.baths;
      document.getElementById('floors').value = p.floors;
      document.getElementById('zipcode').value = p.zip;
      document.getElementById('yr_built').value = p.yr;
      document.getElementById('grade').value = p.grade;
      document.getElementById('view').value = p.view;
    }

    async function fetchHistory() {
      try {
        const res = await fetch('/predictions?limit=10');
        const data = await res.json();
        const tbody = document.getElementById('historyBody');
        tbody.innerHTML = '';
        if (data.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted);">No predictions recorded yet.</td></tr>';
          return;
        }
        data.forEach(item => {
          const snap = item.input_snapshot || {};
          const area = snap.area || {};
          const beds = snap.bedrooms || {};
          const loc = snap.location || {};
          const dt = item.predicted_at ? new Date(item.predicted_at).toLocaleTimeString() : 'N/A';
          const price = item.predicted_price ? '$' + Number(item.predicted_price).toLocaleString() : 'N/A';

          const row = document.createElement('tr');
          row.innerHTML = `
            <td><code>${item.property_id || 'N/A'}</code></td>
            <td>${loc.zipcode || 'N/A'}</td>
            <td>${beds.bedrooms || '-'}b / ${beds.bathrooms || '-'}ba (${area.sqft_living || '-'} sqft)</td>
            <td style="color: var(--success); font-weight: 700;">${price}</td>
            <td style="color: var(--text-muted); font-size: 0.75rem;">${dt}</td>
          `;
          tbody.appendChild(row);
        });
      } catch (err) {
        console.error(err);
      }
    }

    document.getElementById('predictForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const btn = document.getElementById('btnSubmit');
      btn.innerText = 'Calculating...';
      btn.disabled = true;

      const payload = {
        property_id: document.getElementById('prop_id').value || undefined,
        area: {
          sqft_living: parseFloat(document.getElementById('sqft_living').value),
          sqft_lot: parseFloat(document.getElementById('sqft_lot').value),
          sqft_above: parseFloat(document.getElementById('sqft_above').value) || undefined,
          sqft_basement: parseFloat(document.getElementById('sqft_basement').value) || 0
        },
        bedrooms: {
          bedrooms: parseFloat(document.getElementById('bedrooms').value),
          bathrooms: parseFloat(document.getElementById('bathrooms').value),
          floors: parseFloat(document.getElementById('floors').value)
        },
        location: {
          zipcode: document.getElementById('zipcode').value
        },
        property_age: {
          yr_built: parseInt(document.getElementById('yr_built').value),
          yr_renovated: parseInt(document.getElementById('yr_renovated').value) || 0
        },
        amenities: {
          waterfront: parseInt(document.getElementById('waterfront').value),
          view: parseInt(document.getElementById('view').value),
          condition: parseInt(document.getElementById('condition').value),
          grade: parseInt(document.getElementById('grade').value)
        }
      };

      try {
        const res = await fetch('/predict', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'Prediction failed');

        document.getElementById('resultBox').style.display = 'block';
        document.getElementById('resPrice').innerText = result.formatted_price;
        document.getElementById('resModel').innerText = result.model_name + ' v' + result.model_version;
        document.getElementById('resDistance').innerText = 'Downtown: ' + result.distance_to_seattle_miles + ' mi';
        document.getElementById('resAmenity').innerText = 'Amenity Score: ' + result.amenity_score;
        document.getElementById('resSaved').innerText = result.stored_in_db ? '✓ Synced to MongoDB' : '⚠ DB offline';

        fetchHistory();
      } catch (err) {
        alert('Error: ' + err.message);
      } finally {
        btn.innerText = 'Calculate Estimated Value';
        btn.disabled = false;
      }
    });

    function resetForm() {
      document.getElementById('predictForm').reset();
      document.getElementById('resultBox').style.display = 'none';
    }

    // Initial load
    fetchHistory();
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
