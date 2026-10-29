"""
features.py - Feature engineering and transformation pipeline for King County House Sales.
Maps raw variables into 5 domain groups: Area, Bedrooms, Location, Property Age, Amenities.
Strictly ensures zero data leakage by computing target encodings on training folds only.
"""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from typing import Dict, List, Optional

# Seattle Downtown reference coordinates (Pike Place / Central Downtown)
SEATTLE_LAT = 47.6062
SEATTLE_LONG = -122.3321


def haversine_distance(
    lat: np.ndarray,
    lon: np.ndarray,
    lat_target: float = SEATTLE_LAT,
    lon_target: float = SEATTLE_LONG
) -> np.ndarray:
    """
    Computes Great Circle Haversine distance in miles between coordinates and target (Downtown Seattle).
    """
    lat1, lon1, lat2, lon2 = map(np.radians, [lat, lon, lat_target, lon_target])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    miles = 3958.8 * c
    return miles


def calculate_amenity_score(
    waterfront: np.ndarray,
    view: np.ndarray,
    condition: np.ndarray,
    grade: np.ndarray
) -> np.ndarray:
    """
    Computes a composite amenity score:
    - waterfront (0 or 1, weight 3.0)
    - view (0 to 4 normalized, weight 1.5)
    - condition (1 to 5 normalized, weight 1.0)
    - grade (1 to 13 normalized, weight 2.5)
    """
    norm_view = np.clip(view / 4.0, 0, 1)
    norm_cond = np.clip((condition - 1.0) / 4.0, 0, 1)
    norm_grade = np.clip((grade - 1.0) / 12.0, 0, 1)
    return (waterfront * 3.0) + (norm_view * 1.5) + (norm_cond * 1.0) + (norm_grade * 2.5)


def engineer_features(df: pd.DataFrame, sale_year_default: int = 2015) -> pd.DataFrame:
    """
    Transforms raw property features into engineered domain variables across the 5 groups:
    1. Area: sqft_living, sqft_lot, sqft_above, sqft_basement, living_to_lot_ratio, has_basement
    2. Bedrooms: bedrooms, bathrooms, floors, bed_to_bath_ratio, sqft_per_room
    3. Location: zipcode, lat, long, distance_to_seattle
    4. Property Age: age, is_renovated, years_since_renovation
    5. Amenities: waterfront, view, condition, grade, amenity_score
    """
    res = df.copy()

    # Determine sale year
    if 'date' in res.columns:
        date_series = pd.to_datetime(res['date'])
        sale_year = date_series.dt.year
    elif 'sale_year' in res.columns:
        sale_year = res['sale_year']
    else:
        sale_year = sale_year_default

    # 1. Area Features
    res['living_to_lot_ratio'] = res['sqft_living'] / np.maximum(res['sqft_lot'], 1.0)
    res['has_basement'] = (res['sqft_basement'] > 0).astype(int)

    # 2. Bedrooms & Layout Features
    bathrooms_safe = np.maximum(res['bathrooms'], 0.5)
    res['bed_to_bath_ratio'] = res['bedrooms'] / bathrooms_safe
    total_rooms = res['bedrooms'] + res['bathrooms']
    res['sqft_per_room'] = res['sqft_living'] / np.maximum(total_rooms, 1.0)

    # 3. Location Features
    res['distance_to_seattle'] = haversine_distance(res['lat'].values, res['long'].values)
    res['zipcode_str'] = res['zipcode'].astype(str)

    # 4. Property Age Features
    res['age'] = np.maximum(sale_year - res['yr_built'], 0)
    is_renovated = (res['yr_renovated'] > 0).astype(int)
    res['is_renovated'] = is_renovated

    # years_since_renovation: if renovated, years since then; else original age
    res['years_since_renovation'] = np.where(
        res['yr_renovated'] > 0,
        np.maximum(sale_year - res['yr_renovated'], 0),
        res['age']
    )

    # 5. Amenities Features
    res['amenity_score'] = calculate_amenity_score(
        res['waterfront'].values,
        res['view'].values,
        res['condition'].values,
        res['grade'].values
    )

    return res


class ZipcodeTargetEncoder(BaseEstimator, TransformerMixin):
    """
    Leak-free Target Encoder for zipcode.
    Learns median log(price) per zipcode strictly on training data.
    Fills unseen zipcodes at test/inference time with global training median.
    """
    def __init__(self, target_col: str = 'log_price'):
        self.target_col = target_col
        self.zipcode_map_: Dict[str, float] = {}
        self.global_median_: float = 0.0

    def fit(self, X: pd.DataFrame, y: Optional[pd.Series] = None):
        if y is None:
            raise ValueError("y must be provided to fit ZipcodeTargetEncoder.")
        
        y_series = pd.Series(y).reset_index(drop=True)
        zip_series = X['zipcode_str'].reset_index(drop=True)
        
        grouped = y_series.groupby(zip_series).median()
        self.zipcode_map_ = grouped.to_dict()
        self.global_median_ = float(y_series.median())
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X_out = X.copy()
        X_out['zipcode_target_enc'] = X_out['zipcode_str'].map(self.zipcode_map_).fillna(self.global_median_).astype(float)
        return X_out


class HousePricePipeline:
    """
    End-to-end production inference pipeline wrapper.
    Accepts raw property dictionaries or DataFrames, applies feature transformations,
    computes target encodings with learned training statistics, and predicts price ($).
    """
    def __init__(self, model, feature_names, zipcode_map, global_median_log_price, seattle_coords):
        self.model = model
        self.feature_names = feature_names
        self.zipcode_map = zipcode_map
        self.global_median_log_price = global_median_log_price
        self.seattle_coords = seattle_coords

    def transform(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        df = df_raw.copy()
        # Ensure date/sale_year
        if 'sale_year' not in df.columns:
            if 'date' in df.columns:
                df['sale_year'] = pd.to_datetime(df['date']).dt.year
            else:
                df['sale_year'] = 2015

        # 1. Area
        df['sqft_living'] = df['sqft_living'].astype(float)
        df['sqft_lot'] = df['sqft_lot'].astype(float)
        df['sqft_above'] = df['sqft_above'].astype(float)
        df['sqft_basement'] = df['sqft_basement'].astype(float)
        df['living_to_lot_ratio'] = df['sqft_living'] / np.maximum(df['sqft_lot'], 1.0)
        df['has_basement'] = (df['sqft_basement'] > 0).astype(int)

        # 2. Bedrooms & Layout
        df['bedrooms'] = df['bedrooms'].astype(float)
        df['bathrooms'] = df['bathrooms'].astype(float)
        df['floors'] = df['floors'].astype(float)
        df['bed_to_bath_ratio'] = df['bedrooms'] / np.maximum(df['bathrooms'], 0.5)
        df['sqft_per_room'] = df['sqft_living'] / np.maximum(df['bedrooms'] + df['bathrooms'], 1.0)

        # 3. Location
        df['lat'] = df['lat'].astype(float)
        df['long'] = df['long'].astype(float)
        df['distance_to_seattle'] = haversine_distance(
            df['lat'].values, df['long'].values,
            self.seattle_coords['lat'], self.seattle_coords['long']
        )
        df['zipcode_str'] = df['zipcode'].astype(str)
        df['zipcode_num'] = pd.to_numeric(df['zipcode'], errors='coerce').fillna(98000)
        df['zipcode_target_enc'] = df['zipcode_str'].map(self.zipcode_map).fillna(self.global_median_log_price).astype(float)

        # 4. Property Age
        df['age'] = np.maximum(df['sale_year'] - df['yr_built'], 0)
        df['is_renovated'] = (df['yr_renovated'] > 0).astype(int)
        df['years_since_renovation'] = np.where(
            df['yr_renovated'] > 0,
            np.maximum(df['sale_year'] - df['yr_renovated'], 0),
            df['age']
        )

        # 5. Amenities
        df['amenity_score'] = calculate_amenity_score(
            df['waterfront'].values,
            df['view'].values,
            df['condition'].values,
            df['grade'].values
        )

        return df[self.feature_names]

    def predict(self, df_raw: pd.DataFrame) -> np.ndarray:
        X = self.transform(df_raw)
        pred_log = self.model.predict(X)
        pred_price = np.expm1(pred_log)
        return np.maximum(pred_price, 10000.0)


# Standard feature column list used across all models
NUMERIC_FEATURES = [
    'sqft_living', 'sqft_lot', 'sqft_above', 'sqft_basement',
    'living_to_lot_ratio', 'has_basement',
    'bedrooms', 'bathrooms', 'floors', 'bed_to_bath_ratio', 'sqft_per_room',
    'lat', 'long', 'distance_to_seattle', 'zipcode_target_enc',
    'age', 'is_renovated', 'years_since_renovation',
    'waterfront', 'view', 'condition', 'grade', 'amenity_score'
]

CATEGORICAL_FEATURES = ['zipcode_str']

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


if __name__ == "__main__":
    df_sample = pd.DataFrame([{
        'price': 540000.0,
        'bedrooms': 3,
        'bathrooms': 2.0,
        'sqft_living': 2000,
        'sqft_lot': 6000,
        'floors': 1.5,
        'waterfront': 0,
        'view': 1,
        'condition': 3,
        'grade': 8,
        'sqft_above': 1500,
        'sqft_basement': 500,
        'yr_built': 1975,
        'yr_renovated': 0,
        'zipcode': 98178,
        'lat': 47.5112,
        'long': -122.257,
        'date': '20141013T000000'
    }])

    fe = engineer_features(df_sample)
    print("Engineered features sample shape:", fe.shape)
    for col in NUMERIC_FEATURES:
        if col != 'zipcode_target_enc':
            print(f"  {col:25s}: {fe[col].iloc[0]}")
