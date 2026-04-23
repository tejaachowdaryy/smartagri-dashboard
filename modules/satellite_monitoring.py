"""
modules/satellite_monitoring.py
=================================
Satellite monitoring logic – wraps GEE utilities and field GeoJSON management.
All heavy computation is delegated to gee_utils; this module provides
the business-logic layer consumed by the Streamlit monitoring page.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np

from modules import gee_utils

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Field management
# ─────────────────────────────────────────────────────────────────────────────

def load_fields(geojson_path: str = "./data/fields.geojson") -> gpd.GeoDataFrame:
    """
    Load field boundaries from a GeoJSON file.

    Returns a GeoDataFrame with at least columns:
        Field_Id, Crop_Type, Season, geometry
    """
    path = Path(geojson_path)
    if not path.exists():
        logger.warning("fields.geojson not found at %s; using synthetic fields.", path)
        return _synthetic_fields()

    gdf = gpd.read_file(path)

    # Normalise column names
    rename = {}
    for col in gdf.columns:
        if col.lower() == "field_id":
            rename[col] = "Field_Id"
        if col.lower() == "crop_type":
            rename[col] = "Crop_Type"
    if rename:
        gdf = gdf.rename(columns=rename)

    # Ensure Field_Id is integer
    if "Field_Id" in gdf.columns:
        gdf["Field_Id"] = gdf["Field_Id"].astype(int)

    return gdf


def get_field_bbox(gdf: gpd.GeoDataFrame, field_id: int) -> list[float]:
    """Return [minx, miny, maxx, maxy] for a specific field."""
    row = gdf[gdf["Field_Id"] == field_id]
    if row.empty:
        raise ValueError(f"Field {field_id} not found in GeoDataFrame.")
    b = row.total_bounds  # (minx, miny, maxx, maxy)
    return [float(b[0]), float(b[1]), float(b[2]), float(b[3])]


def add_field(
    geojson_path: str,
    geometry_geojson: dict,
    crop_type: str,
    season: str,
) -> int:
    """
    Append a new field polygon to the GeoJSON file.

    Returns the new Field_Id.
    """
    gdf = load_fields(geojson_path)
    new_id = int(gdf["Field_Id"].max()) + 1 if not gdf.empty else 1

    new_row = gpd.GeoDataFrame.from_features(
        [{"type": "Feature", "geometry": geometry_geojson, "properties": {}}]
    )
    new_row["Field_Id"] = new_id
    new_row["Crop_Type"] = crop_type
    new_row["Season"]    = season

    updated = gpd.GeoDataFrame(
        pd.concat([gdf, new_row], ignore_index=True), crs="EPSG:4326"
    )
    updated.to_file(geojson_path, driver="GeoJSON")
    logger.info("Added field %d (%s) to %s", new_id, crop_type, geojson_path)
    return new_id


# ─────────────────────────────────────────────────────────────────────────────
# Satellite data retrieval
# ─────────────────────────────────────────────────────────────────────────────

def get_available_dates(
    gdf: gpd.GeoDataFrame,
    field_id: int,
    year: int,
    gee_ok: bool = False,
) -> list[str]:
    bbox = get_field_bbox(gdf, field_id)
    return gee_utils.get_available_dates(bbox, year, gee_ok=gee_ok)


def get_ndvi_map(
    gdf: gpd.GeoDataFrame,
    field_id: int,
    date: str,
    gee_ok: bool = False,
    size: int = 64,
) -> np.ndarray:
    """Return 2-D NDVI float32 array for a field on a given date."""
    bbox = get_field_bbox(gdf, field_id)
    return gee_utils.fetch_ndvi_array(bbox, date, gee_ok=gee_ok, size=size)


def get_lai_map(
    gdf: gpd.GeoDataFrame,
    field_id: int,
    date: str,
    gee_ok: bool = False,
    size: int = 64,
) -> np.ndarray:
    """Return 2-D LAI float32 array for a field on a given date."""
    bbox = get_field_bbox(gdf, field_id)
    return gee_utils.fetch_lai_array(bbox, date, gee_ok=gee_ok, size=size)


def get_true_color(
    gdf: gpd.GeoDataFrame,
    field_id: int,
    date: str,
    gee_ok: bool = False,
    size: int = 128,
) -> np.ndarray:
    """Return (H, W, 3) uint8 RGB true-colour image."""
    bbox = get_field_bbox(gdf, field_id)
    return gee_utils.fetch_true_color(bbox, date, gee_ok=gee_ok, size=size)


def get_timeseries(
    gdf: gpd.GeoDataFrame,
    field_id: int,
    year: int,
    dates: list[str],
    gee_ok: bool = False,
) -> dict:
    """Return NDVI/LAI time-series dict: {dates, ndvi, lai}."""
    bbox = get_field_bbox(gdf, field_id)
    return gee_utils.fetch_timeseries(bbox, year, dates, gee_ok=gee_ok)


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _synthetic_fields() -> gpd.GeoDataFrame:
    """Generate a small synthetic GeoDataFrame for demo / testing."""
    from shapely.geometry import Polygon

    fields = [
        {
            "Field_Id":  1,
            "Crop_Type": "Wheat",
            "Season":    "Rabi",
            "geometry":  Polygon([(33.1, 14.3), (33.15, 14.3), (33.15, 14.35), (33.1, 14.35)]),
        },
        {
            "Field_Id":  2,
            "Crop_Type": "Sorghum",
            "Season":    "Kharif",
            "geometry":  Polygon([(33.2, 14.3), (33.25, 14.3), (33.25, 14.35), (33.2, 14.35)]),
        },
        {
            "Field_Id":  3,
            "Crop_Type": "Maize",
            "Season":    "Kharif",
            "geometry":  Polygon([(33.3, 14.3), (33.35, 14.3), (33.35, 14.35), (33.3, 14.35)]),
        },
    ]
    return gpd.GeoDataFrame(fields, crs="EPSG:4326")


# Needed inside add_field (lazy import to avoid circular)
import pandas as pd
