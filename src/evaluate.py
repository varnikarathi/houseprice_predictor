"""
evaluate.py - Evaluation functions, metrics calculation, and reporting plots.
Computes R², MAE, RMSE, MAPE in both original currency ($) and log scale.
Generates:
1. Residuals plot (residuals vs predicted)
2. Predicted vs actual scatter plot
3. Feature importance plot (Random Forest MDI & Permutation Importance)
4. Model comparison bar chart
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from sklearn.inspection import permutation_importance

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def compute_metrics(y_true_log: np.ndarray, y_pred_log: np.ndarray) -> Dict[str, float]:
    """
    Computes regression metrics on both log-scale and inverted original currency ($).
    """
    y_true_price = np.expm1(y_true_log)
    y_pred_price = np.maximum(np.expm1(y_pred_log), 0.0)

    # Log metrics
    r2_log = float(r2_score(y_true_log, y_pred_log))
    mae_log = float(mean_absolute_error(y_true_log, y_pred_log))
    rmse_log = float(np.sqrt(mean_squared_error(y_true_log, y_pred_log)))

    # Price metrics (original currency)
    r2_price = float(r2_score(y_true_price, y_pred_price))
    mae_price = float(mean_absolute_error(y_true_price, y_pred_price))
    rmse_price = float(np.sqrt(mean_squared_error(y_true_price, y_pred_price)))
    mape_price = float(mean_absolute_percentage_error(y_true_price, y_pred_price)) * 100.0

    return {
        "r2_price": round(r2_price, 4),
        "mae_price": round(mae_price, 2),
        "rmse_price": round(rmse_price, 2),
        "mape_price": round(mape_price, 2),
        "r2_log": round(r2_log, 4),
        "mae_log": round(mae_log, 4),
        "rmse_log": round(rmse_log, 4)
    }


def plot_residuals(
    y_true_price: np.ndarray,
    y_pred_price: np.ndarray,
    model_name: str = "Random Forest",
    save_path: str = "reports/figures/residuals_plot.png"
):
    residuals = y_true_price - y_pred_price
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(y_pred_price / 1e3, residuals / 1e3, alpha=0.35, color='#1f77b4', edgecolors='none', s=20)
    ax.axhline(0, color='#d62728', linestyle='--', linewidth=1.8, label='Zero Error')
    ax.set_title(f"Figure 7: Residuals vs. Predicted Price ({model_name})", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Predicted Price ($ in Thousands)", fontsize=11)
    ax.set_ylabel("Residuals ($ in Thousands, Actual - Predicted)", fontsize=11)
    ax.set_xlim(0, 3000)
    ax.set_ylim(-1000, 1000)
    ax.legend(frameon=True, facecolor='white')
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {save_path}")


def plot_predicted_vs_actual(
    y_true_price: np.ndarray,
    y_pred_price: np.ndarray,
    r2_val: float,
    mae_val: float,
    model_name: str = "Random Forest",
    save_path: str = "reports/figures/predicted_vs_actual.png"
):
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(y_true_price / 1e3, y_pred_price / 1e3, alpha=0.35, color='#2ca02c', edgecolors='none', s=20)
    max_val = min(3000, max(np.percentile(y_true_price / 1e3, 99.5), np.percentile(y_pred_price / 1e3, 99.5)))
    ax.plot([0, max_val], [0, max_val], color='#d62728', linestyle='--', linewidth=2, label='Ideal Perfect Prediction (y = x)')
    ax.set_title(f"Figure 8: Predicted vs. Actual Sale Price ({model_name})", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Actual Price ($ in Thousands)", fontsize=11)
    ax.set_ylabel("Predicted Price ($ in Thousands)", fontsize=11)
    ax.set_xlim(0, max_val)
    ax.set_ylim(0, max_val)
    stats_text = f"Test R² = {r2_val:.4f}\nMAE = ${mae_val:,.0f}"
    ax.text(0.05, 0.90, stats_text, transform=ax.transAxes, fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='#cccccc', alpha=0.9))
    ax.legend(loc='lower right', frameon=True, facecolor='white')
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {save_path}")


def plot_feature_importances(
    feature_names: List[str],
    importances: np.ndarray,
    perm_importances_mean: np.ndarray = None,
    save_path: str = "reports/figures/feature_importances_rf.png"
):
    df_imp = pd.DataFrame({
        'Feature': feature_names,
        'MDI_Importance': importances
    }).sort_values(by='MDI_Importance', ascending=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(df_imp['Feature'], df_imp['MDI_Importance'] * 100, color='#1f77b4', height=0.65)
    ax.set_title("Figure 9: Random Forest Feature Importances (Mean Decrease in Impurity)", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Relative Importance (%)", fontsize=11)
    ax.set_ylabel("Feature Name", fontsize=11)
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {save_path}")


def plot_model_comparison(
    metrics_summary: Dict[str, Any],
    save_path: str = "reports/figures/model_comparison.png"
):
    models = list(metrics_summary.keys())
    r2_scores = [metrics_summary[m]['test']['r2_price'] for m in models]
    mae_scores = [metrics_summary[m]['test']['mae_price'] / 1e3 for m in models]

    x = np.arange(len(models))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(9, 5))
    ax2 = ax1.twinx()

    b1 = ax1.bar(x - width/2, r2_scores, width, label='Test R² (Price)', color='#1f77b4')
    b2 = ax2.bar(x + width/2, mae_scores, width, label='Test MAE ($k)', color='#ff7f0e')

    ax1.set_ylabel('R² Score', fontsize=11, color='#1f77b4', fontweight='bold')
    ax2.set_ylabel('MAE ($ in Thousands)', fontsize=11, color='#ff7f0e', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, fontsize=10, fontweight='bold')
    ax1.set_ylim(0.7, 1.0)
    ax2.set_ylim(40, 100)
    ax1.set_title("Figure 10: Model Performance Comparison (R² vs. MAE)", fontsize=13, fontweight='bold', pad=12)

    lines = [b1, b2]
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', frameon=True, facecolor='white')
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    fig.savefig(save_path, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {save_path}")


def save_metrics_to_json(metrics: Dict[str, Any], filepath: str = "reports/metrics.json"):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics to {filepath}")
