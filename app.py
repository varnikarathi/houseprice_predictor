#!/usr/bin/env python3
"""
CasaPredict — King County House Price Prediction Application Entrypoint
Author: Varnika Rathi (Reg No: 12318240, Roll No: 66)
GitHub Repository: https://github.com/varnikarathi/houseprice_predictor
"""
import sys
from pathlib import Path
import uvicorn

# Ensure project root in sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.api import app

if __name__ == "__main__":
    print("=" * 70)
    print("  CasaPredict — King County House Price Prediction Microservice")
    print("  Author: Varnika Rathi | Reg No: 12318240 | Roll No: 66")
    print("  Dataset: King County, WA (21,411 Verified Residential Sales)")
    print("  Model: Random Forest Regressor (R² = 0.8724, MAE = $67,108.53)")
    print("  Web Interface: http://127.0.0.1:8000/")
    print("  OpenAPI Docs:  http://127.0.0.1:8000/docs")
    print("  GitHub:        https://github.com/varnikarathi/houseprice_predictor")
    print("=" * 70)
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)
