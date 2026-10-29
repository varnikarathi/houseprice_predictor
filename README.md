# King County House Price Prediction & Automated Valuation Model (AVM)

[![GitHub Repository](https://img.shields.io/badge/GitHub-varnikarathi%2Fhouseprice__predictor-181717?style=for-the-badge&logo=github)](https://github.com/varnikarathi/houseprice_predictor)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Local%20%2F%20Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Tests](https://img.shields.io/badge/pytest-13%20passed-brightgreen?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/varnikarathi/houseprice_predictor)

An end-to-end, production-grade Automated Valuation Model (AVM) estimating residential property sale prices in **King County, Washington** (encompassing Seattle, Bellevue, Redmond, Kirkland, Mercer Island, and surrounding metropolitan areas).

---

## 🔗 Project Links & Documentation
- **Official GitHub Repository**: [https://github.com/varnikarathi/houseprice_predictor](https://github.com/varnikarathi/houseprice_predictor)
- **Comprehensive 15-Page PDF Report (Varnika Rathi, Reg No: 12318240, Roll No: 66)**: [reports/King_County_House_Price_Prediction_Report_Varnika_Rathi.pdf](reports/King_County_House_Price_Prediction_Report_Varnika_Rathi.pdf)
- **Comprehensive Project Markdown Report**: [reports/PROJECT_REPORT.md](reports/PROJECT_REPORT.md)
- **Local Application URL**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📊 Empirical Model Benchmark (Holdout Test Set & 5-Fold CV)

All metrics are evaluated on the 20% holdout test partition (4,283 properties) and verified via 5-Fold Cross Validation on the 80% train set. Trained on $\log(1 + \text{price})$ and inverted with $\exp(y) - 1$ for reporting in original currency (USD):

| Algorithm | Test $R^2$ (Price) | Test $R^2$ (Log) | Test MAE ($) | Test RMSE ($) | Test MAPE (%) | 5-Fold CV MAE ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Gradient Boosting** | **0.8883** | **0.8997** | **$65,379.60** | **$120,861.42** | **12.26%** | $64,365.58 |
| **Random Forest (Production)** | **0.8724** | **0.8979** | **$67,108.53** | **$129,170.55** | **12.26%** | **$66,415.45** |
| **Linear Regression (OLS Baseline)** | 0.8685 | 0.8814 | $73,485.98 | $131,149.60 | 13.65% | $72,899.05 |
| **Ridge Regression ($\alpha = 1.0$)** | 0.8668 | 0.8812 | $73,689.05 | $131,990.76 | 13.66% | $73,018.30 |

> **Specification Criterion**: The primary Random Forest model achieves **Test $R^2 = 0.8724$** (and **Test Log $R^2 = 0.8979$**), substantially exceeding the project acceptance threshold of $R^2 \ge 0.80$.

---

## 📁 Repository Directory Structure

```text
houseprice_predictor/
├── data/
│   ├── raw/
│   │   ├── kc_house_data.csv               # Raw King County dataset (21,613 records)
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
│   ├── PROJECT_REPORT.md                   # Comprehensive technical report
│   ├── House_Price_Prediction_Report.pdf   # Formatted PDF publication report
│   ├── House_Price_Prediction_Report.docx  # Word document format
│   ├── House_Price_Prediction.pptx         # Executive slide deck
│   ├── metrics.json                        # Machine-readable evaluation metrics
│   └── figures/                            # 12 high-resolution analysis figures
├── src/
│   ├── api.py                              # FastAPI REST microservice + UI mount
│   ├── data.py                             # Data cleaning and deduplication
│   ├── db.py                               # MongoDB client and persistence layer
│   ├── eda.py                              # Statistical EDA generation
│   ├── evaluate.py                         # Evaluation and residual diagnostic scripts
│   ├── features.py                         # Feature engineering & target encoders
│   └── train.py                            # Model training & serialization pipeline
├── static/
│   ├── style.css                           # Soft pastel design system tokens
│   └── images/
│       └── pastel_hero_house.jpg           # Hero visual asset
├── templates/
│   └── index.html                          # Modern pastel CasaPredict web UI
├── tests/
│   ├── test_api.py                         # FastAPI endpoint integration tests
│   ├── test_db.py                          # MongoDB connection & CRUD tests
│   └── test_features.py                    # Feature calculation & leakage tests
├── requirements.txt                        # Pinned dependencies
└── README.md                               # Project documentation
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+
- MongoDB running locally on `localhost:27017` (or remote URI in `.env`)

### 2. Installation
```bash
git clone https://github.com/varnikarathi/houseprice_predictor.git
cd houseprice_predictor
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Automated Test Suite
```bash
python -m pytest tests/ -v
```

### 4. Start the Application Server
```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser to access the modern pastel **CasaPredict** valuation interface.
