"""
test_db.py - Integration tests for MongoDB persistence, collections, and queries.
"""

import uuid
from datetime import datetime, timezone
import pytest

from src.db import get_mongo_client, get_database, insert_property, get_property, insert_prediction, get_predictions


@pytest.fixture(scope="module")
def mongo_db():
    client = get_mongo_client()
    db = get_database(client)
    yield db


def test_mongo_connection(mongo_db):
    res = mongo_db.command("ping")
    assert res.get("ok") == 1.0


def test_insert_and_get_property(mongo_db):
    test_id = f"test_{uuid.uuid4().hex[:8]}"
    prop_data = {
        "property_id": test_id,
        "area_sqft": 2400.0,
        "lot_sqft": 7500.0,
        "sqft_above": 1800.0,
        "sqft_basement": 600.0,
        "bedrooms": 4.0,
        "bathrooms": 2.5,
        "floors": 2.0,
        "location": {
            "zipcode": "98052",
            "lat": 47.67,
            "long": -122.12
        },
        "age_years": 25,
        "yr_built": 1999,
        "yr_renovated": 0,
        "renovated": False,
        "amenities": {
            "waterfront": 0,
            "view": 1,
            "condition": 4,
            "grade": 8
        },
        "actual_price": 725000.0,
        "created_at": datetime.now(timezone.utc)
    }

    inserted_id = insert_property(prop_data, mongo_db)
    assert inserted_id == test_id

    retrieved = get_property(test_id, mongo_db)
    assert retrieved is not None
    assert retrieved["property_id"] == test_id
    assert retrieved["area_sqft"] == 2400.0
    assert retrieved["location"]["zipcode"] == "98052"


def test_insert_and_get_prediction(mongo_db):
    test_id = f"test_{uuid.uuid4().hex[:8]}"
    pred_data = {
        "property_id": test_id,
        "model_name": "Random Forest Regressor",
        "model_version": "1.0.0",
        "predicted_price": 685000.50,
        "input_snapshot": {"bedrooms": 3, "sqft_living": 2100},
        "predicted_at": datetime.now(timezone.utc)
    }

    pred_id = insert_prediction(pred_data, mongo_db)
    assert pred_id is not None

    preds = get_predictions(limit=5, db=mongo_db)
    assert len(preds) > 0
    assert any(p["property_id"] == test_id for p in preds)
