"""
test_features.py - Unit tests for feature engineering transformations and encoders.
"""

import numpy as np
import pandas as pd
import pytest

from src.features import (
    haversine_distance, calculate_amenity_score, engineer_features,
    ZipcodeTargetEncoder, SEATTLE_LAT, SEATTLE_LONG
)


def test_haversine_distance():
    # Target downtown coordinates to itself should be 0.0
    dist_zero = haversine_distance(np.array([SEATTLE_LAT]), np.array([SEATTLE_LONG]))
    assert np.isclose(dist_zero[0], 0.0, atol=1e-3)

    # Bellevue Downtown (~6 miles from Seattle Downtown)
    bellevue_lat, bellevue_long = 47.6101, -122.2015
    dist_bellevue = haversine_distance(np.array([bellevue_lat]), np.array([bellevue_long]))
    assert 5.0 < dist_bellevue[0] < 8.0


def test_calculate_amenity_score():
    # Base home with no view, average condition, average grade (7/13)
    score_base = calculate_amenity_score(
        waterfront=np.array([0]),
        view=np.array([0]),
        condition=np.array([3]),
        grade=np.array([7])
    )[0]
    assert 1.0 < score_base < 3.0

    # Luxury waterfront mansion
    score_luxury = calculate_amenity_score(
        waterfront=np.array([1]),
        view=np.array([4]),
        condition=np.array([5]),
        grade=np.array([13])
    )[0]
    # 3.0 (waterfront) + 1.5 (view) + 1.0 (cond) + 2.5 (grade) = 8.0
    assert np.isclose(score_luxury, 8.0)


def test_engineer_features():
    df_raw = pd.DataFrame([{
        'price': 450000.0,
        'bedrooms': 3,
        'bathrooms': 2.0,
        'sqft_living': 1800,
        'sqft_lot': 6000,
        'floors': 1.0,
        'waterfront': 0,
        'view': 0,
        'condition': 3,
        'grade': 7,
        'sqft_above': 1400,
        'sqft_basement': 400,
        'yr_built': 1990,
        'yr_renovated': 0,
        'zipcode': 98103,
        'lat': 47.66,
        'long': -122.34,
        'date': '20141015T000000'
    }])

    feat = engineer_features(df_raw)
    assert 'living_to_lot_ratio' in feat.columns
    assert 'has_basement' in feat.columns
    assert feat['has_basement'].iloc[0] == 1
    assert 'distance_to_seattle' in feat.columns
    assert 'age' in feat.columns
    assert feat['age'].iloc[0] == 2014 - 1990
    assert 'amenity_score' in feat.columns
    assert feat.isnull().sum().sum() == 0


def test_zipcode_target_encoder_no_leakage():
    X_train = pd.DataFrame({'zipcode_str': ['98001', '98001', '98002', '98002']})
    y_train = pd.Series([10.0, 12.0, 14.0, 16.0])

    te = ZipcodeTargetEncoder()
    te.fit(X_train, y_train)

    assert te.zipcode_map_['98001'] == 11.0
    assert te.zipcode_map_['98002'] == 15.0
    assert te.global_median_ == 13.0

    # Transform with known and unknown zipcodes
    X_test = pd.DataFrame({'zipcode_str': ['98001', '99999']})
    transformed = te.transform(X_test)
    assert transformed['zipcode_target_enc'].iloc[0] == 11.0
    # Unseen zipcode should fall back to global training median
    assert transformed['zipcode_target_enc'].iloc[1] == 13.0
