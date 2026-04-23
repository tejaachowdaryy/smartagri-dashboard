# SmartAgri Intelligence Platform

AI-powered agricultural dashboard combining satellite monitoring (GEE/Sentinel-2)
with ML-based crop recommendation and yield estimation.

## Requirements
- **Python 3.11** (recommended)
- Windows / Mac / Linux

## Quick Start

```bash
# 1. Create virtual environment
py -3.11 -m venv venv

# 2. Activate it
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

## Features
- 🏠 Dashboard Home — KPI cards, field map, crop distribution
- 🌱 Crop Recommendation — ML prediction + weather forecast
- 🛰️ Satellite Monitoring — NDVI / LAI / True Color per field
- 📊 Field Analytics — Yield estimation + fertilizer tips
- ➕ Add New Field — Draw boundary on satellite map

## Enable Real GEE Data
1. Sign up at https://earthengine.google.com
2. Run: `earthengine authenticate`
3. Edit `config.yaml` → set `use_demo_mode: false`
4. Restart the app

## Rebuild Models (if needed)
```bash
python retrain.py
```
