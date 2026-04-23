"""
modules/crop_recommendation.py
================================
Loads trained Random Forest models (crop classifier + yield regressor)
and exposes clean prediction functions used by the Streamlit UI.

Models saved with pickle protocol=2 for Python 3.8+ compatibility.
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Singleton model cache
# ─────────────────────────────────────────────────────────────────────────────

_CACHE: dict = {}


def _load_models(models_dir: str | Path = "./models") -> dict:
    """Load models once and cache in module-level _CACHE."""
    global _CACHE
    if _CACHE:
        return _CACHE

    base = Path(models_dir)
    try:
        with open(base / "crop_model.pkl",  "rb") as f:
            _CACHE["crop_model"]  = pickle.load(f)
        with open(base / "yield_model.pkl", "rb") as f:
            _CACHE["yield_model"] = pickle.load(f)
        with open(base / "encoders.pkl",    "rb") as f:
            _CACHE["encoders"]    = pickle.load(f)
        with open(base / "model_meta.json", encoding="utf-8") as f:
            _CACHE["meta"]        = json.load(f)
        logger.info("Models loaded from %s", base)
    except FileNotFoundError as exc:
        logger.error("Model file not found: %s", exc)
        _CACHE = {}
    return _CACHE


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_model_meta(models_dir: str = "./models") -> dict:
    """Return dropdown options for the UI."""
    cache = _load_models(models_dir)
    if not cache:
        return {
            "states":  ["Andaman and Nicobar Islands", "Kerala", "Karnataka"],
            "crops":   ["Arecanut", "Banana", "Coconut", "Groundnut"],
            "soils":   ["Black", "Clayey", "Laterite", "Sandy", "loamy"],
            "seasons": ["Kharif", "Rabi", "Whole Year"],
        }
    return cache["meta"]


def predict_crop(
    state: str,
    soil_type: str,
    season: str,
    area: float,
    models_dir: str = "./models",
) -> dict:
    """
    Recommend the most suitable crop and provide class probabilities.

    Returns
    -------
    {
        "crop":       str,
        "confidence": float,
        "all_probs":  dict[str, float],
        "top3":       list[dict],
    }
    """
    cache = _load_models(models_dir)
    if not cache:
        return _demo_crop_prediction(state, soil_type)

    enc  = cache["encoders"]
    meta = cache["meta"]
    mdl  = cache["crop_model"]

    try:
        state_enc  = _safe_encode(enc["state"],  state.strip())
        soil_enc   = _safe_encode(enc["soil"],   soil_type.strip())
        season_enc = _safe_encode(enc["season"], season.strip())
    except ValueError as exc:
        logger.warning("Encoding error: %s", exc)
        return _demo_crop_prediction(state, soil_type)

    X = pd.DataFrame(
        [[state_enc, soil_enc, season_enc, area]],
        columns=["state_enc", "soil_enc", "season_enc", "Area"],
    )
    proba      = mdl.predict_proba(X)[0]
    crop_names = meta["crops"]

    top_idx  = int(np.argmax(proba))
    all_prob = {name: float(p) for name, p in zip(crop_names, proba)}
    top3     = sorted(all_prob.items(), key=lambda x: x[1], reverse=True)[:3]

    return {
        "crop":       crop_names[top_idx],
        "confidence": float(proba[top_idx]),
        "all_probs":  all_prob,
        "top3":       [{"crop": c, "prob": p} for c, p in top3],
    }


def predict_yield(
    state: str,
    crop: str,
    season: str,
    soil_type: str,
    area: float,
    models_dir: str = "./models",
) -> dict:
    """
    Predict crop yield (production per hectare).

    Returns
    -------
    {"yield_per_ha": float, "total_production": float}
    """
    cache = _load_models(models_dir)
    if not cache:
        return {"yield_per_ha": 2.5, "total_production": area * 2.5}

    enc = cache["encoders"]
    mdl = cache["yield_model"]

    try:
        state_enc  = _safe_encode(enc["state"],  state.strip())
        crop_enc   = _safe_encode(enc["crop"],   crop.strip())
        season_enc = _safe_encode(enc["season"], season.strip())
        soil_enc   = _safe_encode(enc["soil"],   soil_type.strip())
    except ValueError:
        return {"yield_per_ha": 2.5, "total_production": area * 2.5}

    X = pd.DataFrame(
        [[state_enc, crop_enc, season_enc, soil_enc, area]],
        columns=["state_enc", "crop_enc", "season_enc", "soil_enc", "Area"],
    )
    y_pred = float(mdl.predict(X)[0])

    return {
        "yield_per_ha":     round(y_pred, 3),
        "total_production": round(y_pred * area, 2),
    }


def get_feature_importance(models_dir: str = "./models") -> pd.DataFrame:
    """Return feature importances for the crop classification model."""
    cache = _load_models(models_dir)
    if not cache:
        return pd.DataFrame({
            "feature":    ["State", "Soil Type", "Season", "Area"],
            "importance": [0.4, 0.3, 0.2, 0.1],
        })

    mdl         = cache["crop_model"]
    features    = ["State", "Soil Type", "Season", "Area"]
    importances = mdl.feature_importances_
    return (
        pd.DataFrame({"feature": features, "importance": importances})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_encode(encoder, value: str) -> int:
    classes = list(encoder.classes_)
    if value not in classes:
        lower_map = {c.lower(): c for c in classes}
        if value.lower() in lower_map:
            value = lower_map[value.lower()]
        else:
            raise ValueError(f"'{value}' not in training classes.")
    return int(encoder.transform([value])[0])


def _demo_crop_prediction(state: str, soil: str) -> dict:
    mapping = {
        "laterite": "Arecanut",
        "clayey":   "Banana",
        "sandy":    "Groundnut",
        "black":    "Cotton(lint)",
        "loamy":    "Coconut",
    }
    crop  = mapping.get(soil.lower(), "Banana")
    probs = {c: 0.05 for c in ["Arecanut","Banana","Coconut","Cotton(lint)","Groundnut"]}
    probs[crop] = 0.75
    top3  = sorted(probs.items(), key=lambda x: x[1], reverse=True)[:3]
    return {
        "crop":       crop,
        "confidence": 0.75,
        "all_probs":  probs,
        "top3":       [{"crop": c, "prob": p} for c, p in top3],
    }
