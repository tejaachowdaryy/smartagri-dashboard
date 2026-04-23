"""
modules/gee_utils.py  —  Python 3.11 compatible
================================================
Real GEE NDVI/LAI via Sentinel-2 thumbnail URL (no reduceRegion quota issues).
Falls back to synthetic data when GEE is unavailable.
"""
from __future__ import annotations

import io
import logging
import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import ee
    _EE_AVAILABLE = True
except ImportError:
    _EE_AVAILABLE = False
    warnings.warn("earthengine-api not installed – running in demo mode.", stacklevel=2)


# ─────────────────────────────────────────────────────────────────────────────
# Public: initialise
# ─────────────────────────────────────────────────────────────────────────────

def initialise_gee(service_account: str = "", key_file: str = "", project: str = "") -> bool:
    if not _EE_AVAILABLE:
        return False
    try:
        if service_account and key_file:
            creds = ee.ServiceAccountCredentials(service_account, key_file)
            kwargs = {"credentials": creds}
            if project:
                kwargs["project"] = project
            ee.Initialize(**kwargs)
        else:
            # Newer earthengine-api (>= 0.1.370) requires project=
            if project:
                ee.Initialize(project=project)
            else:
                try:
                    ee.Initialize()
                except Exception:
                    raise Exception(
                        "GEE requires a project ID. "
                        "Add 'project: your-project-id' to config.yaml under GEE section."
                    )
        # Quick sanity check
        _ = ee.Number(1).getInfo()
        logger.info("GEE initialised and verified OK")
        return True
    except Exception as exc:
        logger.warning("GEE init failed: %s", exc)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Public: available dates
# ─────────────────────────────────────────────────────────────────────────────

def get_available_dates(bbox, year, max_cloud=20, gee_ok=False):
    if gee_ok and _EE_AVAILABLE:
        try:
            region = ee.Geometry.BBox(*bbox)
            col = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(region)
                .filterDate(f"{year}-01-01", f"{year}-12-31")
                .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
            )
            ms_list = col.aggregate_array("system:time_start").getInfo()
            dates = sorted({_ms_to_date(ms) for ms in ms_list})
            return dates if dates else _demo_dates(year)
        except Exception as exc:
            logger.warning("GEE dates failed: %s", exc)
    return _demo_dates(year)


# ─────────────────────────────────────────────────────────────────────────────
# Public: NDVI array  — uses getThumbURL for real data (works without quota)
# ─────────────────────────────────────────────────────────────────────────────

def fetch_ndvi_array(bbox, date, gee_ok=False, size=64):
    if gee_ok and _EE_AVAILABLE:
        try:
            return _gee_ndvi_via_thumb(bbox, date, size)
        except Exception as exc:
            logger.warning("GEE NDVI fetch failed: %s", exc)

    seed = abs(int(sum(bbox) * 1000 + hash(date))) % 999983
    return _synthetic_index(size, 0.15, 0.85, seed)


def fetch_lai_array(bbox, date, gee_ok=False, size=64):
    if gee_ok and _EE_AVAILABLE:
        try:
            ndvi = _gee_ndvi_via_thumb(bbox, date, size)
            return np.clip(3.618 * ndvi - 0.118, 0, 6).astype(np.float32)
        except Exception as exc:
            logger.warning("GEE LAI fetch failed: %s", exc)

    seed = abs(int(sum(bbox) * 1000 + hash(date))) % 999983
    ndvi = _synthetic_index(size, 0.15, 0.85, seed)
    return np.clip(3.618 * ndvi - 0.118, 0, 6).astype(np.float32)


def fetch_true_color(bbox, date, gee_ok=False, size=128):
    if gee_ok and _EE_AVAILABLE:
        try:
            return _gee_true_color(bbox, date, size)
        except Exception as exc:
            logger.warning("GEE TrueColor failed: %s", exc)

    seed = abs(int(sum(bbox) * 1000 + hash(date))) % 999983
    return _synthetic_true_color(size, seed)


def fetch_timeseries(bbox, year, dates, gee_ok=False):
    if gee_ok and _EE_AVAILABLE:
        try:
            return _gee_timeseries(bbox, year, dates)
        except Exception as exc:
            logger.warning("GEE timeseries failed: %s", exc)

    seed = abs(int(sum(bbox) * 1000)) % 999983
    return _synthetic_timeseries(dates, seed)


# ─────────────────────────────────────────────────────────────────────────────
# Private: real GEE helpers
# ─────────────────────────────────────────────────────────────────────────────

def _best_image(bbox, date, cloud_pct=30):
    """Get least-cloudy Sentinel-2 image within ±5 days of date."""
    region = ee.Geometry.BBox(*bbox)
    d0 = datetime.strptime(date, "%Y-%m-%d")
    start = (d0 - timedelta(days=5)).strftime("%Y-%m-%d")
    end   = (d0 + timedelta(days=5)).strftime("%Y-%m-%d")
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", cloud_pct))
        .sort("CLOUDY_PIXEL_PERCENTAGE")
    )
    return col.first(), region


def _gee_ndvi_via_thumb(bbox, date, size):
    """
    Fetch NDVI as a grayscale PNG thumbnail then convert to float array.
    This method works reliably without hitting reduceRegion pixel limits.
    """
    import requests
    from PIL import Image

    img, region = _best_image(bbox, date)
    ndvi_img = img.normalizedDifference(["B8", "B4"]).rename("ndvi")

    # Export as grayscale PNG: 0=NDVI -1, 255=NDVI +1
    url = ndvi_img.getThumbURL({
        "region":     region,
        "dimensions": size,
        "format":     "png",
        "min":        -0.2,
        "max":        1.0,
        "palette":    ["000000", "ffffff"],   # black=low, white=high
    })

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    pil = Image.open(io.BytesIO(resp.content)).convert("L").resize((size, size))
    arr = np.array(pil, dtype=np.float32) / 255.0
    # Rescale from [0,1] back to [-0.2, 1.0]
    arr = arr * 1.2 - 0.2
    return arr.astype(np.float32)


def _gee_true_color(bbox, date, size):
    import requests
    from PIL import Image

    img, region = _best_image(bbox, date)
    url = img.select(["B4", "B3", "B2"]).getThumbURL({
        "region":     region,
        "dimensions": size,
        "format":     "png",
        "min":        0,
        "max":        3000,
    })
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    pil = Image.open(io.BytesIO(resp.content)).convert("RGB")
    return np.array(pil)


def _gee_timeseries(bbox, year, dates):
    region = ee.Geometry.BBox(*bbox)
    col = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
    )

    def mean_index(img):
        ndvi  = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
        lai   = ndvi.multiply(3.618).subtract(0.118).rename("lai")
        stats = ndvi.addBands(lai).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=60,
            maxPixels=1e6,
        )
        return img.set(stats).set("date", img.date().format("YYYY-MM-dd"))

    mapped = col.map(mean_index)
    ndvi_l = mapped.aggregate_array("ndvi").getInfo()
    lai_l  = mapped.aggregate_array("lai").getInfo()
    date_l = mapped.aggregate_array("date").getInfo()

    # Filter out None values (cloudy/missing images)
    clean = [(d, n, l) for d, n, l in zip(date_l, ndvi_l, lai_l)
             if n is not None and l is not None]
    if not clean:
        return _synthetic_timeseries(dates)
    d_out, n_out, l_out = zip(*clean)
    return {"dates": list(d_out), "ndvi": list(n_out), "lai": list(l_out)}


# ─────────────────────────────────────────────────────────────────────────────
# Private: synthetic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _demo_dates(year):
    months = [(4,15),(5,5),(5,25),(6,15),(7,5),(7,25),(8,15),(9,5),(9,25),(10,15)]
    return [f"{year}-{m:02d}-{d:02d}" for m, d in months]


def _synthetic_index(size, low, high, seed=0):
    from PIL import Image as _Im
    rng    = np.random.default_rng(seed)
    coarse = rng.uniform(low, high, (size // 4 + 1, size // 4 + 1)).astype(np.float32)
    norm   = ((coarse - low) / (high - low) * 255).astype(np.uint8)
    pil    = _Im.fromarray(norm).resize((size, size), getattr(_Im.Resampling, "BICUBIC", 3))
    arr    = np.array(pil, dtype=np.float32) / 255.0
    return arr * (high - low) + low


def _synthetic_true_color(size, seed=42):
    from PIL import Image as _Im
    rng  = np.random.default_rng(seed)
    base = rng.uniform(0.1, 0.5, (size // 8 + 1, size // 8 + 1, 3)).astype(np.float32)
    resample = getattr(_Im, "BICUBIC", getattr(_Im.Resampling, "BICUBIC", 3))
    pil  = _Im.fromarray((base * 255).astype(np.uint8)).resize((size, size), resample)
    return np.array(pil)


def _synthetic_timeseries(dates, seed=7):
    n    = len(dates)
    x    = np.linspace(0, np.pi, n)
    ndvi = 0.25 + 0.55 * np.sin(x) + np.random.default_rng(seed).normal(0, 0.03, n)
    lai  = np.clip(3.618 * ndvi - 0.118, 0, 6)
    return {"dates": dates, "ndvi": ndvi.tolist(), "lai": lai.tolist()}


def _ms_to_date(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _next_day(date):
    return (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
