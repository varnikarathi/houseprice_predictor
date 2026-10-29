"""
eda.py - Generates exploratory data analysis visualizations and saves high-resolution figures.
Visualizations:
1. price_distribution.png
2. log_price_distribution.png
3. correlation_heatmap.png
4. price_vs_sqft_living.png
5. price_by_zipcode_top_bottom_10.png
6. outliers_analysis.png
"""

import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Set style
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8


def generate_eda_plots(
    raw_path: str = "data/raw/kc_house_data.csv",
    output_dir: str = "reports/figures"
):
    os.makedirs(output_dir, exist_ok=True)
    df_raw = pd.read_csv(raw_path)
    logger.info(f"Loaded raw dataset ({len(df_raw)} records) for EDA generation.")

    # 1. Price Distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(df_raw['price'] / 1e3, kde=True, bins=60, color='#1f77b4', ax=ax)
    median_p = df_raw['price'].median() / 1e3
    mean_p = df_raw['price'].mean() / 1e3
    ax.axvline(median_p, color='#d62728', linestyle='--', linewidth=2, label=f'Median: ${median_p:.0f}k')
    ax.axvline(mean_p, color='#2ca02c', linestyle=':', linewidth=2, label=f'Mean: ${mean_p:.0f}k')
    ax.set_title("Figure 1: Distribution of Sale Prices in King County (Original Currency)", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Sale Price ($ in Thousands)", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.set_xlim(0, 3000)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    plt.tight_layout()
    p1 = os.path.join(output_dir, "price_distribution.png")
    fig.savefig(p1, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {p1}")

    # 2. Log-Price Distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    log_p = np.log1p(df_raw['price'])
    sns.histplot(log_p, kde=True, bins=50, color='#2ca02c', ax=ax)
    ax.axvline(log_p.mean(), color='#d62728', linestyle='--', linewidth=2, label=f'Mean: {log_p.mean():.2f} (Std: {log_p.std():.2f})')
    ax.set_title("Figure 2: Distribution of Log-Transformed Sale Price [log1p(price)]", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("log1p(price)", fontsize=11)
    ax.set_ylabel("Frequency", fontsize=11)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9)
    plt.tight_layout()
    p2 = os.path.join(output_dir, "log_price_distribution.png")
    fig.savefig(p2, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {p2}")

    # 3. Correlation Heatmap
    corr_cols = [
        'price', 'sqft_living', 'grade', 'sqft_above', 'bathrooms',
        'lat', 'bedrooms', 'view', 'sqft_basement', 'waterfront',
        'floors', 'yr_built', 'condition', 'sqft_lot'
    ]
    corr_matrix = df_raw[corr_cols].corr()
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        corr_matrix, annot=True, fmt='.2f', cmap='Blues', cbar=True,
        linewidths=0.5, linecolor='#f0f0f0', ax=ax, annot_kws={"size": 9}
    )
    ax.set_title("Figure 3: Pearson Correlation Heatmap of Primary Housing Attributes", fontsize=13, fontweight='bold', pad=14)
    plt.tight_layout()
    p3 = os.path.join(output_dir, "correlation_heatmap.png")
    fig.savefig(p3, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {p3}")

    # 4. Price vs Sqft Living (colored by King County Construction Grade)
    fig, ax = plt.subplots(figsize=(9, 6))
    sample = df_raw.sample(n=min(5000, len(df_raw)), random_state=42)
    scatter = ax.scatter(
        sample['sqft_living'], sample['price'] / 1e3,
        c=sample['grade'], cmap='viridis', alpha=0.6, edgecolors='none', s=25
    )
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("King County Grade (1-13)", fontsize=11)
    ax.set_title("Figure 4: Property Sale Price vs. Interior Living Area (sqft_living)", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Living Area (sqft)", fontsize=11)
    ax.set_ylabel("Sale Price ($ in Thousands)", fontsize=11)
    ax.set_ylim(0, 4000)
    ax.set_xlim(0, 8000)
    plt.tight_layout()
    p4 = os.path.join(output_dir, "price_vs_sqft_living.png")
    fig.savefig(p4, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {p4}")

    # 5. Price by Zipcode (Top 10 and Bottom 10 median prices)
    zip_medians = df_raw.groupby('zipcode')['price'].median().sort_values()
    bottom_10 = zip_medians.head(10)
    top_10 = zip_medians.tail(10)
    combined = pd.concat([bottom_10, top_10]) / 1e3
    colors = ['#1f77b4'] * 10 + ['#d62728'] * 10

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh([str(z) for z in combined.index], combined.values, color=colors, height=0.7)
    ax.axvline(median_p, color='black', linestyle='--', linewidth=1.5, label=f'County Median: ${median_p:.0f}k')
    ax.set_title("Figure 5: Median Sale Price by Zipcode (Top 10 & Bottom 10 King County Zipcodes)", fontsize=13, fontweight='bold', pad=12)
    ax.set_xlabel("Median Price ($ in Thousands)", fontsize=11)
    ax.set_ylabel("Zipcode", fontsize=11)
    ax.legend(frameon=True, facecolor='white')
    plt.tight_layout()
    p5 = os.path.join(output_dir, "price_by_zipcode_top_bottom_10.png")
    fig.savefig(p5, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {p5}")

    # 6. Outlier Analysis (e.g. 33-bedroom anomaly and bedroom distribution)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Left: Bedroom count distribution showing 33 outlier
    bed_counts = df_raw['bedrooms'].value_counts().sort_index()
    ax1.bar(bed_counts.index, bed_counts.values, color='#4575b4', width=0.8)
    ax1.set_yscale('log')
    ax1.set_title("Bedroom Distribution (Log Scale)", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Number of Bedrooms", fontsize=10)
    ax1.set_ylabel("Count of Properties (Log Scale)", fontsize=10)
    # Highlight 33 bedroom outlier
    ax1.annotate(
        "Erroneous Entry (33 Beds)\n1,620 sqft, 1.75 baths\nID: 2402100895",
        xy=(33, 1), xytext=(22, 20),
        arrowprops=dict(facecolor='#d73027', shrink=0.05, width=1.5, headwidth=8),
        fontsize=9, fontweight='bold', color='#a50026'
    )

    # Right: Living area vs Bedrooms scatter
    ax2.scatter(df_raw['bedrooms'], df_raw['sqft_living'], alpha=0.4, color='#313695', s=20)
    ax2.scatter([33], [1620], color='#d73027', s=100, edgecolors='black', label='33-Bed Outlier (1,620 sqft)')
    ax2.set_title("Sqft Living vs. Bedrooms", fontsize=12, fontweight='bold')
    ax2.set_xlabel("Bedrooms", fontsize=10)
    ax2.set_ylabel("Living Area (sqft)", fontsize=10)
    ax2.legend(frameon=True, facecolor='white')

    fig.suptitle("Figure 6: Data Cleaning and Outlier Diagnostics (King County Sales)", fontsize=13, fontweight='bold', y=0.98)
    plt.tight_layout()
    p6 = os.path.join(output_dir, "outliers_analysis.png")
    fig.savefig(p6, dpi=300)
    plt.close(fig)
    logger.info(f"Saved {p6}")

    print("All 6 EDA figures successfully generated and saved to", output_dir)


if __name__ == "__main__":
    generate_eda_plots()
