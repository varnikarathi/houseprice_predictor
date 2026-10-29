"""
data.py - Data ingestion, inspection, and cleaning pipeline for King County House Sales.
"""

import os
import sys
import logging
from typing import Tuple, Dict, Any
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    'price', 'bedrooms', 'bathrooms', 'sqft_living', 'sqft_lot', 'floors',
    'waterfront', 'view', 'condition', 'grade', 'yr_built', 'yr_renovated',
    'zipcode', 'lat', 'long'
]


def load_raw_data(filepath: str = "data/raw/kc_house_data.csv") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Loads raw King County housing sales dataset and performs verification.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Raw data file not found at {filepath}. Please place kc_house_data.csv in data/raw/.")

    logger.info(f"Loading raw dataset from {filepath}...")
    df = pd.read_csv(filepath)

    diagnostics = {
        "shape": df.shape,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": df.isnull().sum().to_dict(),
        "columns_present": list(df.columns),
    }

    print("\n" + "=" * 50)
    print("DATASET DIAGNOSTICS")
    print("=" * 50)
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns\n")
    print("Column Data Types & Non-Null Counts:")
    for col in df.columns:
        print(f"  - {col:15s}: {str(df[col].dtype):10s} (Nulls: {df[col].isnull().sum()})")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        msg = f"CRITICAL: Missing required columns: {missing}"
        logger.error(msg)
        raise ValueError(msg)
    else:
        print(f"\n[OK] All {len(REQUIRED_COLUMNS)} required columns are present.")

    print("\nSummary Statistics:")
    print(df.describe().T[['count', 'mean', 'std', 'min', '50%', 'max']])
    print("=" * 50 + "\n")

    return df, diagnostics


def clean_data(
    df: pd.DataFrame,
    output_path: str = "data/processed/kc_house_data_clean.csv"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Cleans raw data by deduplicating by property ID and removing documented outliers.
    All dropped records are logged transparently.
    """
    initial_count = len(df)
    logger.info(f"Starting data cleaning on {initial_count} records...")

    # 1. Parse date and deduplicate by property ID (keep latest sale)
    df_clean = df.copy()
    df_clean['date_dt'] = pd.to_datetime(df_clean['date'])
    df_sorted = df_clean.sort_values(by=['id', 'date_dt'], ascending=[True, False])
    df_dedup = df_sorted.drop_duplicates(subset=['id'], keep='first').copy()
    duplicates_dropped = initial_count - len(df_dedup)
    logger.info(f"Deduplication: dropped {duplicates_dropped} earlier sales (retained latest transaction per property).")

    # 2. Document and remove anomalies
    # Anomaly A: 33 bedrooms entry (likely typo for 3 bedrooms in a 1,620 sqft home)
    bedroom_33_mask = (df_dedup['bedrooms'] == 33)
    bedroom_33_count = int(bedroom_33_mask.sum())
    if bedroom_33_count > 0:
        logger.info(f"Identified {bedroom_33_count} anomalous row with 33 bedrooms (id: {df_dedup.loc[bedroom_33_mask, 'id'].tolist()}).")

    # Anomaly B: Zero bedrooms or zero bathrooms (non-standard residential properties)
    zero_bed_bath_mask = (df_dedup['bedrooms'] == 0) | (df_dedup['bathrooms'] == 0)
    zero_bed_bath_count = int(zero_bed_bath_mask.sum())
    logger.info(f"Identified {zero_bed_bath_count} records with 0 bedrooms or 0 bathrooms.")

    # Anomaly C: Unrealistic property dimensions or extreme price outliers
    valid_domain_mask = (
        (df_dedup['bedrooms'] >= 1) &
        (df_dedup['bedrooms'] <= 10) &
        (df_dedup['bathrooms'] >= 0.5) &
        (df_dedup['sqft_living'] >= 300) &
        (df_dedup['price'] >= 50000) &
        (df_dedup['price'] <= 5000000)
    )

    outlier_count = int((~valid_domain_mask).sum())
    logger.info(f"Domain outlier filter: removing {outlier_count} non-residential or extreme outlier records.")

    df_final = df_dedup[valid_domain_mask].copy()
    final_count = len(df_final)
    total_dropped = initial_count - final_count

    summary = {
        "initial_rows": initial_count,
        "duplicate_sales_dropped": duplicates_dropped,
        "retained_unique_properties": len(df_dedup),
        "outlier_rows_dropped": outlier_count,
        "final_cleaned_rows": final_count,
        "total_rows_removed": total_dropped,
        "percentage_retained": round((final_count / initial_count) * 100, 2)
    }

    logger.info(f"Cleaning complete: {final_count} rows retained ({summary['percentage_retained']}% of raw dataset).")

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df_final.to_csv(output_path, index=False)
        logger.info(f"Cleaned dataset saved to {output_path}")

    return df_final, summary


if __name__ == "__main__":
    df_raw, diag = load_raw_data()
    df_clean, summary = clean_data(df_raw)
    print("\nCleaning Summary:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
