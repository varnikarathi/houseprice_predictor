"""
test_api.py - Integration tests for FastAPI endpoints: /health, /metrics, /predict, /predictions.
"""

import pytest
from fastapi.testclient import TestClient

from src.api import app, load_artifacts

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def init_app():
    load_artifacts()


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["model_loaded"] is True
    assert data["database_connected"] is True


def test_metrics_endpoint():
    res = client.get("/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "Random Forest" in data
    assert "Linear Regression" in data
    assert "test" in data["Random Forest"]
    assert data["Random Forest"]["test"]["r2_log"] > 0.85


def test_predict_endpoint_valid():
    payload = {
        "property_id": "test_api_prop_001",
        "area": {
            "sqft_living": 2200.0,
            "sqft_lot": 6000.0,
            "sqft_above": 1700.0,
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
            "yr_built": 1980,
            "yr_renovated": 0,
            "sale_year": 2015
        },
        "amenities": {
            "waterfront": 0,
            "view": 1,
            "condition": 3,
            "grade": 8
        },
        "actual_price": 580000.0
    }

    res = client.post("/predict", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["property_id"] == "test_api_prop_001"
    assert data["predicted_price"] > 100000.0
    assert data["stored_in_db"] is True
    assert "$" in data["formatted_price"]


def test_predict_validation_error():
    # Invalid bedrooms (> 12)
    invalid_payload = {
        "area": {"sqft_living": 2000, "sqft_lot": 5000},
        "bedrooms": {"bedrooms": 25, "bathrooms": 2.0, "floors": 1.0},
        "location": {"zipcode": "98103"},
        "property_age": {"yr_built": 1990},
        "amenities": {"waterfront": 0, "view": 0, "condition": 3, "grade": 7}
    }
    res = client.post("/predict", json=invalid_payload)
    assert res.status_code == 422


def test_get_predictions_endpoint():
    res = client.get("/predictions?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_property_endpoint():
    res = client.get("/properties/test_api_prop_001")
    assert res.status_code == 200
    data = res.json()
    assert data["property_id"] == "test_api_prop_001"
