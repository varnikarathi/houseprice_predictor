# King County House Price Prediction

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Local%20%2F%20Atlas-forestgreen.svg)](https://www.mongodb.com/)
[![Tests](https://img.shields.io/badge/pytest-13%20passed-brightgreen.svg)](tests/)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](https://creativecommons.org/publicdomain/zero/1.0/)

An end-to-end, production-grade Automated Valuation Model (AVM) estimating residential property sale prices in King County, Washington (encompassing Seattle, Bellevue, Redmond, and surrounding areas). 

The system maps property attributes across five core dimensions (**Area**, **Bedrooms**, **Location**, **Property Age**, and **Amenities**), enforces a zero-data-leakage pipeline protocol, persists property snapshots and predictions in **MongoDB**, and serves real-time valuations via a **FastAPI** REST microservice and interactive web dashboard.

---

## 📊 Empirical Model Results (Holdout Test Set & 5-Fold CV)

All metrics are evaluated on the 20% holdout test partition (4,283 properties) and verified via 5-Fold Cross Validation on the 80% train set. Trained on $\log(1 + \text{price})$ and inverted with $\exp(y) - 1$ for reporting in original currency (USD):

| Algorithm | Test Log R² | Test Price R² | Test MAE ($) | Test RMSE ($) | Test MAPE (%) | 5-Fold CV Price MAE ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Linear Regression (Baseline)** | 0.8814 | 0.8685 | $73,485.98 | $131,149.60 | 13.65% | $72,899.05 ± $1,252.58 |
| **Ridge Regression (Sanity Check)** | 0.8812 | 0.8668 | $73,689.05 | $131,990.76 | 13.66% | $73,018.30 ± $1,334.43 |
| **Random Forest (Primary Tuned)** | **0.8979** | **0.8724** | **$67,108.53** | **$129,170.55** | **12.26%** | **$66,415.45 ± $1,818.61** |
| **Gradient Boosting (Comparison)** | 0.8997 | 0.8883 | $65,379.60 | $120,861.42 | 12.26% | $64,365.58 ± $2,279.22 |

> **Specification Criterion**: The primary Random Forest model achieves **Test R² = 0.8724** (and **Test Log R² = 0.8979**), substantially exceeding the project acceptance threshold of $R^2 \ge 0.80$.

---

## 🗂️ Project Directory Structure

```text
houseprice_predictor/
├── data/
│   ├── raw/
│   │   ├── kc_house_data.csv               # Raw Kaggle dataset (21,613 records)
│   │   └── housesalesprediction.zip
│   └── processed/
│       └── kc_house_data_clean.csv         # Cleaned, deduplicated data (21,411 records)
├── models/
│   ├── best_model.joblib                   # Serialized production pipeline artifact
│   └── model_metadata.json                 # Model schema, hyperparameters, and metrics
├── notebooks/
│   ├── 01_eda.ipynb                        # Executed Exploratory Data Analysis notebook
│   └── 02_modeling.ipynb                   # Executed modeling & evaluation notebook
├── reports/
│   ├── figures/
│   │   ├── price_distribution.png          # Figure 1: Raw price histogram & skewness
│   │   ├── log_price_distribution.png      # Figure 2: log1p(price) distribution
│   │   ├── correlation_heatmap.png         # Figure 3: Correlation heatmap
│   │   ├── price_vs_sqft_living.png        # Figure 4: Price vs living area by grade
│   │   ├── price_by_zipcode_top_bottom_10.png # Figure 5: Top/bottom zipcode medians
│   │   ├── outliers_analysis.png           # Figure 6: 33-bed and domain outlier breakdown
│   │   ├── residuals_plot.png              # Figure 7: Residuals vs. predicted price
│   │   ├── predicted_vs_actual.png         # Figure 8: Predicted vs. actual scatter
│   │   ├── feature_importances_rf.png      # Figure 9: RF MDI feature importances
│   │   ├── model_comparison.png            # Figure 10: R² vs. MAE comparison chart
│   │   ├── system_architecture.png         # Figure 11: End-to-end system architecture
│   │   └── dashboard_demo_preview.png      # Figure 12: Production UI demo preview
│   ├── metrics.json                        # Machine-readable evaluation metrics
│   ├── House_Price_Prediction_Report.docx  # Full 10-section formal technical report
│   ├── House_Price_Prediction_Report.pdf   # Formally exported PDF technical report
│   └── House_Price_Prediction.pptx         # 12-slide executive presentation
├── src/
│   ├── __init__.py
│   ├── data.py                             # Data loading, validation, and cleaning
│   ├── features.py                         # 5-group feature engineering & target encoding
│   ├── eda.py                              # Generates EDA figures in reports/figures/
│   ├── train.py                            # Model training, 5-fold CV, tuning, persistence
│   ├── evaluate.py                         # Metric computation & evaluation plotting
│   ├── db.py                               # MongoDB schema, indexing, and bulk seeding
│   ├── api.py                              # FastAPI backend and single-page web dashboard
│   ├── build_report.py                     # Compiles Word report and exports PDF
│   └── build_presentation.py               # Compiles PowerPoint presentation deck
├── tests/
│   ├── test_features.py                    # Feature calculation & zero-leakage unit tests
│   ├── test_db.py                          # MongoDB persistence & indexing tests
│   └── test_api.py                         # FastAPI endpoint integration tests
├── requirements.txt                        # Pinned production dependencies
└── README.md                               # Project documentation and run guide
```

---

## ⚙️ Environment Configuration

The application uses standard environment variables:

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `MONGODB_URI` | MongoDB connection URI | `mongodb://localhost:27017` |

If local MongoDB is not running, spin it up using Docker:
```bash
docker run -d -p 27017:27017 --name mongodb mongo:7
```

---

## 🚀 Quickstart & Step-by-Step Reproduction

To reproduce all results, data pipelines, models, reports, and tests from scratch:

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Verify Raw Data & Clean Pipeline
```bash
python src/data.py
```
- Ingests `data/raw/kc_house_data.csv` (21,613 records).
- Deduplicates on property ID, retaining the latest transaction (drops 177 earlier sales).
- Removes the 33-bedroom error (ID 2402100895, 1,620 sqft house with 1.75 baths) and non-residential properties.
- Outputs `data/processed/kc_house_data_clean.csv` (21,411 rows retained, 99.07% retention).

### 3. Generate Exploratory Visualizations
```bash
python src/eda.py
```
- Produces Figures 1 through 6 in `reports/figures/`.

### 4. Train Models, Run 5-Fold CV, Tune RF, and Evaluate
```bash
python src/train.py
```
- Splits data 80/20 train/test (`random_state=42`).
- Computes leak-free zipcode target encodings strictly on training folds.
- Executes 5-fold cross-validation across Linear Regression, Ridge, Random Forest, and Gradient Boosting.
- Tunes Random Forest hyperparameters using `RandomizedSearchCV`.
- Persists production pipeline to `models/best_model.joblib` and metrics to `reports/metrics.json`.
- Produces evaluation plots (Figures 7, 8, 9, 10).

### 5. Seed MongoDB Database
```bash
python src/db.py
```
- Connects to `house_price_db`.
- Sets up compound indexes on `properties` (`property_id` unique, `location.zipcode`) and `predictions` (`property_id`, `predicted_at`).
- Bulk inserts all 21,411 properties into the `properties` collection.

### 6. Run Automated Pytest Suite
```bash
python -m pytest tests/ -v
```
- Runs 13 tests across feature engineering, leak-free target encoding, MongoDB persistence, and FastAPI endpoints.
- Verification: **13 passed in ~3.7s**.

### 7. Compile Technical Report (DOCX & PDF)
```bash
python src/build_report.py
```
- Compiles `reports/House_Price_Prediction_Report.docx` with all 10 formal sections, numbered tables, and figures.
- Automatically exports to `reports/House_Price_Prediction_Report.pdf` via Microsoft Word COM automation.

### 8. Compile Executive Presentation (PPTX)
```bash
python src/build_presentation.py
```
- Generates `reports/House_Price_Prediction.pptx` (12 widescreen 16:9 slides with speaker notes and verified metrics).

### 9. Launch FastAPI & Interactive Web UI
```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```
- Access Interactive Web Dashboard: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Access Interactive Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Access Health Status: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🌐 FastAPI REST Endpoints

### 1. `POST /predict`
Accepts the 5 input groups, validates schema with Pydantic, performs model inference, and logs documents into MongoDB.

**Sample Request Body:**
```json
{
  "property_id": "seattle_home_01",
  "area": {
    "sqft_living": 2150.0,
    "sqft_lot": 5800.0,
    "sqft_above": 1650.0,
    "sqft_basement": 500.0
  },
  "bedrooms": {
    "bedrooms": 3.0,
    "bathrooms": 2.25,
    "floors": 1.5
  },
  "location": {
    "zipcode": "98103",
    "lat": 47.67,
    "long": -122.34
  },
  "property_age": {
    "yr_built": 1982,
    "yr_renovated": 0,
    "sale_year": 2015
  },
  "amenities": {
    "waterfront": 0,
    "view": 0,
    "condition": 3,
    "grade": 8
  }
}
```

**Sample Response Body:**
```json
{
  "property_id": "seattle_home_01",
  "predicted_price": 648500.25,
  "formatted_price": "$648,500.25",
  "model_name": "Random Forest Regressor",
  "model_version": "1.0.0",
  "amenity_score": 2.29,
  "distance_to_seattle_miles": 5.21,
  "stored_in_db": true,
  "predicted_at": "2026-10-28T05:15:00.123456+00:00"
}
```

### 2. `GET /predictions?limit=10`
Returns the latest $N$ valuation documents recorded in MongoDB.

### 3. `GET /properties/{property_id}`
Retrieves a stored property document by its identifier.

### 4. `GET /metrics`
Returns model evaluation metrics from `reports/metrics.json`.

### 5. `GET /health`
Returns system status, model loaded flag, and MongoDB connection status.

---

## 🗄️ MongoDB Collections & Schema

### `properties` Collection Sample Document:
```json
{
  "property_id": "7129300520",
  "area_sqft": 1180.0,
  "lot_sqft": 5650.0,
  "sqft_above": 1180.0,
  "sqft_basement": 0.0,
  "bedrooms": 3.0,
  "bathrooms": 1.0,
  "floors": 1.0,
  "location": {
    "zipcode": "98178",
    "lat": 47.5112,
    "long": -122.257
  },
  "age_years": 59,
  "yr_built": 1955,
  "yr_renovated": 0,
  "renovated": false,
  "amenities": {
    "waterfront": 0,
    "view": 0,
    "condition": 3,
    "grade": 7
  },
  "actual_price": 221900.0,
  "created_at": "2026-10-28T05:03:21.792Z"
}
```

### `predictions` Collection Sample Document:
```json
{
  "property_id": "seattle_home_01",
  "model_name": "Random Forest Regressor",
  "model_version": "1.0.0",
  "predicted_price": 648500.25,
  "input_snapshot": { ... },
  "predicted_at": "2026-10-28T05:15:00.123Z"
}
```

---

## 🧪 Automated Testing

Run the test suite with:
```bash
pytest tests/ -v
```

Test coverage includes:
- `test_features.py`: Haversine geodesic distance accuracy, composite amenity score calculations, domain ratio calculations, and target encoder leak-free transform logic.
- `test_db.py`: MongoDB connection ping, property insertion & lookup, prediction insertion & query.
- `test_api.py`: FastAPI `/health`, `/metrics`, `/predict` validation (valid inputs vs. 422 Unprocessable Entity), `/predictions` audit feed, and `/properties/{id}` lookup.
