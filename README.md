<<<<<<< HEAD
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
=======
# 🌾 SmartAgri Intelligence Platform

A full-stack precision agriculture web dashboard that integrates 
machine learning, satellite remote sensing, and real-time weather 
forecasting to help farmers make data-driven decisions.

---

## 🚀 Live Demo
👉 [[Click here to open the app](https://smartagri-dashboard.streamlit.app/)

---

## ✨ Features

| Module | Description |
|--------|-------------|
| 🏠 **Dashboard** | Field boundary map, KPI cards, crop distribution |
| 🌱 **Crop Recommendation** | Random Forest ML model (96.8% accuracy) |
| 🛰️ **Satellite Monitoring** | Real Sentinel-2 NDVI/LAI maps via Google Earth Engine |
| 📊 **Field Analytics** | Yield estimation, fertilizer schedule, health leaderboard |
| 🌤️ **Weather Forecast** | 7-day forecast via Open-Meteo API |
| ➕ **Add New Field** | Draw polygon on map or enter GPS coordinates |

---

## 🧠 ML Model

- **Algorithm:** Random Forest Classifier + Regressor
- **Training Data:** 23,320 Indian agricultural records
- **Crop Classifier Accuracy:** 96.8%
- **Yield Regressor R²:** 0.55
- **Top Feature:** Soil Type (70.6% importance)

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit, Folium, Plotly
- **ML:** Scikit-learn, Pandas, NumPy
- **Geospatial:** GeoPandas, Shapely, GeoJSON
- **Satellite:** Google Earth Engine (Sentinel-2)
- **Weather:** Open-Meteo API
- **Language:** Python 3.11

---

## ⚙️ Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/smartagri-dashboard.git
cd smartagri-dashboard

# 2. Create virtual environment
py -3.11 -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
>>>>>>> 31ffacb8eeebe0c5bf4ee05e596a5e5103eecbfe

# 3. Install dependencies
pip install -r requirements.txt

<<<<<<< HEAD
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
=======
# 4. Configure GEE (optional)
# Edit config.yaml → set your project ID
# Run: earthengine authenticate

# 5. Launch the app
streamlit run app.py
```

---

## 🌍 GEE Setup (for real satellite data)

1. Create a Google Earth Engine account at [earthengine.google.com](https://earthengine.google.com)
2. Edit `config.yaml`:
```yaml
GEE:
  use_demo_mode: false
  project: 'your-gee-project-id'
```
3. Run `earthengine authenticate` in terminal

> Without GEE, the app runs in **demo mode** with synthetic data.

---

## 📁 Project Structure
>>>>>>> 31ffacb8eeebe0c5bf4ee05e596a5e5103eecbfe
