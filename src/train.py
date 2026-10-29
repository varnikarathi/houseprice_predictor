"""
train.py - Model training, cross-validation, hyperparameter tuning, and persistence.
Trains:
1. Linear Regression (baseline)
2. Ridge Regression (regularized linear sanity check)
3. Random Forest Regressor (primary tuned model via RandomizedSearchCV)
4. Gradient Boosting Regressor (comparison model)
Evaluates with 5-fold CV on train + final holdout test evaluation (80/20 split, random_state=42).
Saves best model to models/best_model.joblib and metrics to reports/metrics.json.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import joblib

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sklearn.model_selection import train_test_split, KFold, RandomizedSearchCV
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.inspection import permutation_importance

from src.data import load_raw_data, clean_data
from src.features import (
    engineer_features, ZipcodeTargetEncoder, haversine_distance, calculate_amenity_score,
    HousePricePipeline, SEATTLE_LAT, SEATTLE_LONG
)
from src.evaluate import (
    compute_metrics, plot_residuals, plot_predicted_vs_actual,
    plot_feature_importances, plot_model_comparison, save_metrics_to_json
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_training_pipeline():
    logger.info("Initializing training pipeline...")
    clean_path = "data/processed/kc_house_data_clean.csv"
    if not os.path.exists(clean_path):
        df_raw, _ = load_raw_data()
        df_clean, _ = clean_data(df_raw)
    else:
        df_clean = pd.read_csv(clean_path)

    logger.info(f"Loaded {len(df_clean)} cleaned records.")

    # 1. Feature Engineering
    df_feat = engineer_features(df_clean)
    df_feat['zipcode_num'] = df_feat['zipcode'].astype(int)

    # Modeling feature columns
    tree_feature_cols = [
        'sqft_living', 'sqft_lot', 'sqft_above', 'sqft_basement',
        'living_to_lot_ratio', 'has_basement',
        'bedrooms', 'bathrooms', 'floors', 'bed_to_bath_ratio', 'sqft_per_room',
        'lat', 'long', 'distance_to_seattle', 'zipcode_num', 'zipcode_target_enc',
        'age', 'is_renovated', 'years_since_renovation',
        'waterfront', 'view', 'condition', 'grade', 'amenity_score'
    ]

    # Target
    y_price = df_clean['price'].values
    y_log = np.log1p(y_price)

    # 2. 80/20 Train/Test Split (fixed random_state=42)
    X_train_raw, X_test_raw, y_train_log, y_test_log, y_train_p, y_test_p = train_test_split(
        df_feat, y_log, y_price, test_size=0.20, random_state=42
    )

    logger.info(f"Split data into Train: {len(X_train_raw)} rows, Test: {len(X_test_raw)} rows.")

    # 3. Fit Zipcode Target Encoder on Train strictly (Zero Data Leakage)
    target_encoder = ZipcodeTargetEncoder()
    target_encoder.fit(X_train_raw, y_train_log)
    X_train_enc = target_encoder.transform(X_train_raw)
    X_test_enc = target_encoder.transform(X_test_raw)

    zipcode_map = target_encoder.zipcode_map_
    global_median = target_encoder.global_median_

    # Prepare matrices for linear models
    num_cols_linear = [c for c in tree_feature_cols if c != 'zipcode_num']
    lr_preprocessor = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols_linear),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['zipcode_str'])
        ]
    )

    # 4. 5-Fold Cross Validation on Train Set
    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    logger.info("Executing 5-Fold Cross-Validation on training set...")

    cv_results = {
        "Linear Regression": {"r2_log": [], "mae_price": [], "r2_price": []},
        "Ridge Regression": {"r2_log": [], "mae_price": [], "r2_price": []},
        "Random Forest": {"r2_log": [], "mae_price": [], "r2_price": []},
        "Gradient Boosting": {"r2_log": [], "mae_price": [], "r2_price": []}
    }

    # Baseline RF and GB instances for CV
    rf_cv_model = RandomForestRegressor(n_estimators=100, max_depth=20, min_samples_leaf=2, max_features=0.7, random_state=42, n_jobs=-1)
    gb_cv_model = GradientBoostingRegressor(n_estimators=120, max_depth=5, learning_rate=0.1, random_state=42)

    for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X_train_raw)):
        # Fold train & val
        fold_X_tr_raw = X_train_raw.iloc[tr_idx]
        fold_y_tr_log = y_train_log[tr_idx]
        fold_X_val_raw = X_train_raw.iloc[val_idx]
        fold_y_val_log = y_train_log[val_idx]
        fold_y_val_p = y_train_p[val_idx]

        # Inner fold target encoder (strictly leak-free)
        fold_te = ZipcodeTargetEncoder()
        fold_te.fit(fold_X_tr_raw, fold_y_tr_log)
        fold_X_tr = fold_te.transform(fold_X_tr_raw)
        fold_X_val = fold_te.transform(fold_X_val_raw)

        # 1. Linear Regression
        fold_lr_prep = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), num_cols_linear),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['zipcode_str'])
            ]
        )
        fold_lr = Pipeline([('prep', fold_lr_prep), ('reg', LinearRegression())])
        fold_lr.fit(fold_X_tr, fold_y_tr_log)
        p_lr = fold_lr.predict(fold_X_val)
        m_lr = compute_metrics(fold_y_val_log, p_lr)
        cv_results["Linear Regression"]["r2_log"].append(m_lr["r2_log"])
        cv_results["Linear Regression"]["mae_price"].append(m_lr["mae_price"])
        cv_results["Linear Regression"]["r2_price"].append(m_lr["r2_price"])

        # 2. Ridge
        fold_ridge_prep = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), num_cols_linear),
                ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['zipcode_str'])
            ]
        )
        fold_ridge = Pipeline([('prep', fold_ridge_prep), ('reg', Ridge(alpha=10.0))])
        fold_ridge.fit(fold_X_tr, fold_y_tr_log)
        p_ridge = fold_ridge.predict(fold_X_val)
        m_ridge = compute_metrics(fold_y_val_log, p_ridge)
        cv_results["Ridge Regression"]["r2_log"].append(m_ridge["r2_log"])
        cv_results["Ridge Regression"]["mae_price"].append(m_ridge["mae_price"])
        cv_results["Ridge Regression"]["r2_price"].append(m_ridge["r2_price"])

        # 3. Random Forest
        rf_cv_model.fit(fold_X_tr[tree_feature_cols], fold_y_tr_log)
        p_rf = rf_cv_model.predict(fold_X_val[tree_feature_cols])
        m_rf = compute_metrics(fold_y_val_log, p_rf)
        cv_results["Random Forest"]["r2_log"].append(m_rf["r2_log"])
        cv_results["Random Forest"]["mae_price"].append(m_rf["mae_price"])
        cv_results["Random Forest"]["r2_price"].append(m_rf["r2_price"])

        # 4. Gradient Boosting
        gb_cv_model.fit(fold_X_tr[tree_feature_cols], fold_y_tr_log)
        p_gb = gb_cv_model.predict(fold_X_val[tree_feature_cols])
        m_gb = compute_metrics(fold_y_val_log, p_gb)
        cv_results["Gradient Boosting"]["r2_log"].append(m_gb["r2_log"])
        cv_results["Gradient Boosting"]["mae_price"].append(m_gb["mae_price"])
        cv_results["Gradient Boosting"]["r2_price"].append(m_gb["r2_price"])

    logger.info("5-Fold CV Completed.")

    # 5. Fit Full Training Set & Hyperparameter Tuning on Random Forest
    logger.info("Running RandomizedSearchCV tuning for Random Forest...")
    rf_param_dist = {
        'n_estimators': [100, 150, 200],
        'max_depth': [15, 20, 25, None],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['sqrt', 0.5, 0.7]
    }
    rf_search = RandomizedSearchCV(
        estimator=RandomForestRegressor(random_state=42, n_jobs=-1),
        param_distributions=rf_param_dist,
        n_iter=6,
        cv=3,
        scoring='r2',
        random_state=42,
        n_jobs=-1
    )
    rf_search.fit(X_train_enc[tree_feature_cols], y_train_log)
    best_rf = rf_search.best_estimator_
    logger.info(f"Best RF Parameters: {rf_search.best_params_}")

    # Full Linear Regression
    full_lr = Pipeline([('prep', lr_preprocessor), ('reg', LinearRegression())])
    full_lr.fit(X_train_enc, y_train_log)

    # Full Ridge Regression
    full_ridge_prep = ColumnTransformer(
        transformers=[
            ('num', StandardScaler(), num_cols_linear),
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), ['zipcode_str'])
        ]
    )
    full_ridge = Pipeline([('prep', full_ridge_prep), ('reg', Ridge(alpha=10.0))])
    full_ridge.fit(X_train_enc, y_train_log)

    # Full Gradient Boosting
    full_gb = GradientBoostingRegressor(n_estimators=150, max_depth=5, learning_rate=0.08, random_state=42)
    full_gb.fit(X_train_enc[tree_feature_cols], y_train_log)

    # 6. Evaluate all on Holdout Test Set (20%)
    logger.info("Evaluating all models on holdout test set...")
    pred_test_lr = full_lr.predict(X_test_enc)
    pred_test_ridge = full_ridge.predict(X_test_enc)
    pred_test_rf = best_rf.predict(X_test_enc[tree_feature_cols])
    pred_test_gb = full_gb.predict(X_test_enc[tree_feature_cols])

    test_metrics_lr = compute_metrics(y_test_log, pred_test_lr)
    test_metrics_ridge = compute_metrics(y_test_log, pred_test_ridge)
    test_metrics_rf = compute_metrics(y_test_log, pred_test_rf)
    test_metrics_gb = compute_metrics(y_test_log, pred_test_gb)

    # Aggregate CV summary stats
    def summarize_cv(metrics_dict):
        return {
            "cv_r2_log_mean": round(float(np.mean(metrics_dict["r2_log"])), 4),
            "cv_r2_log_std": round(float(np.std(metrics_dict["r2_log"])), 4),
            "cv_r2_price_mean": round(float(np.mean(metrics_dict["r2_price"])), 4),
            "cv_r2_price_std": round(float(np.std(metrics_dict["r2_price"])), 4),
            "cv_mae_price_mean": round(float(np.mean(metrics_dict["mae_price"])), 2),
            "cv_mae_price_std": round(float(np.std(metrics_dict["mae_price"])), 2)
        }

    all_metrics = {
        "Linear Regression": {
            "test": test_metrics_lr,
            "cv": summarize_cv(cv_results["Linear Regression"])
        },
        "Ridge Regression": {
            "test": test_metrics_ridge,
            "cv": summarize_cv(cv_results["Ridge Regression"])
        },
        "Random Forest": {
            "test": test_metrics_rf,
            "cv": summarize_cv(cv_results["Random Forest"]),
            "best_params": rf_search.best_params_
        },
        "Gradient Boosting": {
            "test": test_metrics_gb,
            "cv": summarize_cv(cv_results["Gradient Boosting"])
        }
    }

    print("\n" + "=" * 65)
    print("MODEL EVALUATION COMPARISON TABLE (HOLDOUT TEST SET)")
    print("=" * 65)
    print(f"{'Model':<22} | {'Log R²':<8} | {'Price R²':<9} | {'MAE ($)':<12} | {'MAPE':<8}")
    print("-" * 65)
    for model_name, data in all_metrics.items():
        tm = data["test"]
        print(f"{model_name:<22} | {tm['r2_log']:<8.4f} | {tm['r2_price']:<9.4f} | ${tm['mae_price']:<11,.2f} | {tm['mape_price']:.2f}%")
    print("=" * 65 + "\n")

    # 7. Generate Evaluation Figures
    logger.info("Generating evaluation figures...")
    pred_rf_price = np.expm1(pred_test_rf)
    plot_residuals(y_test_p, pred_rf_price, model_name="Random Forest Regressor")
    plot_predicted_vs_actual(y_test_p, pred_rf_price, r2_val=test_metrics_rf["r2_price"], mae_val=test_metrics_rf["mae_price"])
    plot_feature_importances(tree_feature_cols, best_rf.feature_importances_)
    plot_model_comparison(all_metrics)

    # 8. Save Metrics to JSON
    save_metrics_to_json(all_metrics, "reports/metrics.json")

    # 9. Package & Persist Best Model (Random Forest)
    os.makedirs("models", exist_ok=True)
    seattle_coords = {"lat": SEATTLE_LAT, "long": SEATTLE_LONG}
    production_pipeline = HousePricePipeline(
        model=best_rf,
        feature_names=tree_feature_cols,
        zipcode_map=zipcode_map,
        global_median_log_price=global_median,
        seattle_coords=seattle_coords
    )

    model_path = "models/best_model.joblib"
    joblib.dump(production_pipeline, model_path)
    logger.info(f"Persisted production model pipeline to {model_path}")

    # Model metadata
    metadata = {
        "model_name": "Random Forest Regressor",
        "version": "1.0.0",
        "target": "log1p(price) inverted with expm1",
        "feature_count": len(tree_feature_cols),
        "features": tree_feature_cols,
        "input_groups": ["area", "bedrooms", "location", "property_age", "amenities"],
        "best_hyperparameters": rf_search.best_params_,
        "seattle_center": seattle_coords,
        "global_median_log_price": global_median,
        "zipcode_count": len(zipcode_map),
        "test_metrics": test_metrics_rf,
        "cv_metrics": summarize_cv(cv_results["Random Forest"])
    }
    with open("models/model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Saved models/model_metadata.json")

    return production_pipeline, all_metrics


if __name__ == "__main__":
    run_training_pipeline()
