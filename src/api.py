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


from fastapi.staticfiles import StaticFiles

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def serve_frontend():
    """Serves CasaPredict modern pastel web UI for King County."""
    tmpl_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates", "index.html"))
    if os.path.exists(tmpl_path):
        with open(tmpl_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>CasaPredict UI</h1>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
