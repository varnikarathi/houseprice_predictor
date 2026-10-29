"""
db.py - MongoDB client, schema management, indexing, and seed operations.
Uses database 'house_price_db' and collections 'properties' and 'predictions'.
Connection string read from env MONGODB_URI (default: mongodb://localhost:27017).
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import pandas as pd
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, BulkWriteError

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "house_price_db"


def get_mongo_client(uri: Optional[str] = None) -> MongoClient:
    mongo_uri = uri or os.getenv("MONGODB_URI", DEFAULT_MONGO_URI)
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        # Verify connection
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB at {mongo_uri}: {e}")
        raise ConnectionError(
            f"Cannot connect to MongoDB at {mongo_uri}. Ensure MongoDB service is running "
            "or start it via docker: docker run -d -p 27017:27017 --name mongo mongo:7"
        ) from e


def get_database(client: Optional[MongoClient] = None):
    c = client or get_mongo_client()
    return c[DB_NAME]


def setup_indexes(db=None):
    """
    Creates required indexes on properties and predictions collections.
    """
    if db is None:
        db = get_database()

    # Index on properties
    db.properties.create_index([("property_id", ASCENDING)], unique=True)
    db.properties.create_index([("location.zipcode", ASCENDING)])
    logger.info("Created indexes on 'properties': property_id (unique), location.zipcode")

    # Index on predictions
    db.predictions.create_index([("property_id", ASCENDING)])
    db.predictions.create_index([("predicted_at", DESCENDING)])
    logger.info("Created indexes on 'predictions': property_id, predicted_at (descending)")


def seed_properties_collection(
    csv_path: str = "data/processed/kc_house_data_clean.csv",
    batch_size: int = 2000
) -> int:
    """
    Seeds 'properties' collection from cleaned King County dataset using bulk insert_many.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Cleaned dataset not found at {csv_path}. Run src/data.py first.")

    db = get_database()
    setup_indexes(db)

    logger.info(f"Loading cleaned dataset for seeding from {csv_path}...")
    df = pd.read_csv(csv_path)

    # Drop existing seeded records to ensure idempotent fresh seeding
    existing_count = db.properties.count_documents({})
    if existing_count > 0:
        logger.info(f"Clearing {existing_count} existing documents in 'properties' collection...")
        db.properties.delete_many({})

    documents = []
    current_time = datetime.utcnow()

    for idx, row in df.iterrows():
        sale_year = int(pd.to_datetime(row['date']).year) if 'date' in row and pd.notnull(row['date']) else 2015
        age = max(sale_year - int(row['yr_built']), 0)
        renovated = bool(row['yr_renovated'] > 0)

        doc = {
            "property_id": str(row['id']),
            "area_sqft": float(row['sqft_living']),
            "lot_sqft": float(row['sqft_lot']),
            "sqft_above": float(row['sqft_above']),
            "sqft_basement": float(row['sqft_basement']),
            "bedrooms": float(row['bedrooms']),
            "bathrooms": float(row['bathrooms']),
            "floors": float(row['floors']),
            "location": {
                "zipcode": str(row['zipcode']),
                "lat": float(row['lat']),
                "long": float(row['long'])
            },
            "age_years": age,
            "yr_built": int(row['yr_built']),
            "yr_renovated": int(row['yr_renovated']),
            "renovated": renovated,
            "amenities": {
                "waterfront": int(row['waterfront']),
                "view": int(row['view']),
                "condition": int(row['condition']),
                "grade": int(row['grade'])
            },
            "actual_price": float(row['price']),
            "created_at": current_time
        }
        documents.append(doc)

        if len(documents) >= batch_size:
            db.properties.insert_many(documents, ordered=False)
            documents = []

    if documents:
        db.properties.insert_many(documents, ordered=False)

    total_inserted = db.properties.count_documents({})
    logger.info(f"Seeding complete! Successfully stored {total_inserted} properties in MongoDB.")
    return total_inserted


def insert_property(prop_data: Dict[str, Any], db=None) -> str:
    """
    Inserts a single property document into 'properties' collection.
    """
    if db is None:
        db = get_database()
    if "created_at" not in prop_data:
        prop_data["created_at"] = datetime.utcnow()
    res = db.properties.update_one(
        {"property_id": prop_data["property_id"]},
        {"$set": prop_data},
        upsert=True
    )
    return prop_data["property_id"]


def get_property(property_id: str, db=None) -> Optional[Dict[str, Any]]:
    """
    Retrieves property by property_id.
    """
    if db is None:
        db = get_database()
    doc = db.properties.find_one({"property_id": str(property_id)}, {"_id": 0})
    return doc


def insert_prediction(pred_data: Dict[str, Any], db=None) -> str:
    """
    Inserts a prediction document into 'predictions' collection.
    """
    if db is None:
        db = get_database()
    if "predicted_at" not in pred_data:
        pred_data["predicted_at"] = datetime.utcnow()
    res = db.predictions.insert_one(pred_data)
    return str(res.inserted_id)


def get_predictions(limit: int = 50, db=None) -> List[Dict[str, Any]]:
    """
    Retrieves latest N predictions from 'predictions' collection.
    """
    if db is None:
        db = get_database()
    cursor = db.predictions.find({}, {"_id": 0}).sort("predicted_at", DESCENDING).limit(limit)
    return list(cursor)


if __name__ == "__main__":
    client = get_mongo_client()
    db = get_database(client)
    print("Connected to MongoDB successfully! Database:", db.name)
    count = seed_properties_collection()
    sample = get_property("7129300520", db)
    print("\nSample Property Document in MongoDB:")
    import pprint
    pprint.pprint(sample)
