#!/usr/bin/env python3
"""
CasaPredict — King County House Price Prediction Application Entrypoint
Author: Varnika Rathi (Reg No: 12318240, Roll No: 66)
GitHub Repository: https://github.com/varnikarathi/houseprice_predictor
"""
import os
import sys
from pathlib import Path

# Resolve current script location
CURRENT_DIR = Path(__file__).resolve().parent

# Check potential locations of src
candidate_dirs = [
    CURRENT_DIR,
    CURRENT_DIR / "pyMongo",
    CURRENT_DIR.parent
]

project_root = None
for candidate in candidate_dirs:
    if (candidate / "src" / "api.py").exists():
        project_root = candidate
        break

if project_root is None:
    raise FileNotFoundError(
        f"Could not locate 'src/api.py' from {CURRENT_DIR}. Checked: {[str(c) for c in candidate_dirs]}"
    )

# Add project root to sys.path and set as working directory
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

os.chdir(str(project_root))

import uvicorn
from src.api import app

if __name__ == "__main__":
    print("=" * 70)
    print("  CasaPredict — King County House Price Prediction Microservice")
    print("  Author: Varnika Rathi | Reg No: 12318240 | Roll No: 66")
    print("  Dataset: King County, WA (21,411 Verified Residential Sales)")
    print("  Model: Random Forest Regressor (R² = 0.8724, MAE = $67,108.53)")
    print(f"  Working Directory: {project_root}")
    print("  Web Interface: http://127.0.0.1:8000/")
    print("  OpenAPI Docs:  http://127.0.0.1:8000/docs")
    print("  GitHub:        https://github.com/varnikarathi/houseprice_predictor")
    print("=" * 70)
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=True)
