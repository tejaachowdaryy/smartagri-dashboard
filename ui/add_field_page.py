"""
ui/add_field_page.py
=====================
Add New Field page — clients can draw a polygon on an interactive map
or enter GPS coordinates manually, fill in crop details, and save to
fields.geojson. The field becomes immediately available in monitoring.
"""

from __future__ import annotations
import json
import os
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import streamlit as st
from shapely.geometry import Polygon
import folium
from folium.plugins import Draw
from streamlit_folium import st_folium

FIELDS_PATH = "./data/fields.geojson"

CROP_OPTIONS = [
    "Wheat", "Maize", "Sorghum", "Millet", "Rice", "Barley",
    "Arecanut", "Banana", "Coconut", "Cotton(lint)",
    "Dry chillies", "Dry ginger", "Groundnut",
    "Sugarcane", "Sunflower", "Soybean", "Other",
]

SEASON_OPTIONS = ["Kharif", "Rabi", "Whole Year", "Summer", "Winter", "Autumn"]

SOIL_OPTIONS   = ["Black", "Clayey", "Laterite", "Sandy", "loamy", "Alluvial", "Red"]


def app():
    st.markdown(
        """
        <div style='padding: 8px 0 24px 0;'>
            <div style='font-family:Syne,sans-serif; font-size:2rem;
                        font-weight:800; color:#2ecc71;'>
                ➕ Add New Field
            </div>
            <div style='color:#8ab89a; font-size:0.9rem; margin-top:4px;'>
                Draw field boundary on the map · Enter crop details · Save to dashboard
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load existing fields ──────────────────────────────────────────────────
    gdf = _load_fields()

    # ── Two column layout ─────────────────────────────────────────────────────
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown(
            "<div style='font-family:Syne,sans-serif; font-weight:700;"
            " color:#e8f5ec; margin-bottom:10px;'>"
            "🗺️ Step 1 — Draw Field Boundary</div>",
            unsafe_allow_html=True,
        )
        st.caption("Use the polygon tool (left toolbar) to draw your field. Click the last point to close the shape.")

        # Centre map on existing fields or default Sudan location
        if not gdf.empty:
            cx = float(gdf.geometry.centroid.x.mean())
            cy = float(gdf.geometry.centroid.y.mean())
        else:
            cx, cy = 33.13, 14.31  # Sudan default

        m = folium.Map(
            location=[cy, cx],
            zoom_start=13,
            tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
            attr="Google Satellite Hybrid",
        )

        # Show existing fields
        for _, row in gdf.iterrows():
            folium.GeoJson(
                row["geometry"].__geo_interface__,
                style_function=lambda _: {
                    "fillColor": "#2ecc71",
                    "color": "white",
                    "weight": 1.5,
                    "fillOpacity": 0.25,
                },
                tooltip=folium.Tooltip(
                    f"Field {row['Field_Id']} – {row.get('Crop_Type','?')}",
                    sticky=True,
                ),
            ).add_to(m)

        # Draw plugin — polygon only
        Draw(
            export=False,
            draw_options={
                "polyline":   False,
                "rectangle":  True,
                "polygon":    True,
                "circle":     False,
                "marker":     False,
                "circlemarker": False,
            },
            edit_options={"edit": True, "remove": True},
        ).add_to(m)

        map_result = st_folium(m, height=450, use_container_width=True)

    with right:
        st.markdown(
            "<div style='font-family:Syne,sans-serif; font-weight:700;"
            " color:#e8f5ec; margin-bottom:10px;'>"
            "📋 Step 2 — Field Details</div>",
            unsafe_allow_html=True,
        )

        client_name = st.text_input("👤 Client / Farm Name", placeholder="e.g. Ahmed Farm")
        crop_type   = st.selectbox("🌾 Crop Type", CROP_OPTIONS)
        season      = st.selectbox("📅 Season", SEASON_OPTIONS)
        soil_type   = st.selectbox("🪨 Soil Type", SOIL_OPTIONS)
        notes       = st.text_area("📝 Notes (optional)", placeholder="e.g. North plot, irrigated", height=80)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        # Manual coordinate fallback
        with st.expander("📌 Or enter coordinates manually"):
            st.caption("Enter corner coordinates as: lon,lat — one per line (min 3 points)")
            coord_text = st.text_area(
                "Coordinates (lon, lat)",
                placeholder="33.120, 14.310\n33.140, 14.310\n33.140, 14.330\n33.120, 14.330",
                height=120,
            )

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        save_btn = st.button("💾  Save Field to Dashboard", use_container_width=True)

    # ── Process save ──────────────────────────────────────────────────────────
    if save_btn:
        coords = _extract_coordinates(map_result, coord_text if coord_text else "")

        if not coords:
            st.error("❌ Please draw a field boundary on the map or enter coordinates manually.")
            return

        if len(coords) < 3:
            st.error("❌ A field needs at least 3 corner points.")
            return

        new_id = _save_field(
            coords=coords,
            crop_type=crop_type,
            season=season,
            soil_type=soil_type,
            client_name=client_name,
            notes=notes,
        )

        st.success(f"✅ Field #{new_id} saved successfully! It is now available in Satellite Monitoring.")
        st.balloons()

        # Show preview
        st.markdown(
            f"""
            <div style='background:#0d2b1a; border:1px solid #2ecc71; border-radius:12px;
                        padding:20px; margin-top:16px;'>
                <div style='font-family:Syne,sans-serif; font-weight:700;
                            color:#2ecc71; margin-bottom:12px;'>📍 Field #{new_id} Summary</div>
                <table style='width:100%; color:#e8f5ec; font-size:0.88rem;'>
                    <tr><td style='color:#8ab89a; width:40%;'>Client</td>
                        <td><b>{client_name or '—'}</b></td></tr>
                    <tr><td style='color:#8ab89a;'>Crop</td>
                        <td><b>{crop_type}</b></td></tr>
                    <tr><td style='color:#8ab89a;'>Season</td>
                        <td><b>{season}</b></td></tr>
                    <tr><td style='color:#8ab89a;'>Soil</td>
                        <td><b>{soil_type}</b></td></tr>
                    <tr><td style='color:#8ab89a;'>Corner points</td>
                        <td><b>{len(coords)}</b></td></tr>
                    <tr><td style='color:#8ab89a;'>Saved at</td>
                        <td><b>{datetime.now().strftime('%Y-%m-%d %H:%M')}</b></td></tr>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border-color:#1e3d28; margin:28px 0;'>", unsafe_allow_html=True)

    # ── Existing fields table ─────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:Syne,sans-serif; font-weight:700;"
        " color:#e8f5ec; margin-bottom:10px;'>"
        "📋 Registered Fields</div>",
        unsafe_allow_html=True,
    )

    if gdf.empty:
        st.info("No fields registered yet. Draw your first field above.")
    else:
        display_cols = [c for c in ["Field_Id","Crop_Type","Season","Client","LastUpdate"] if c in gdf.columns]
        st.dataframe(
            gdf[display_cols].sort_values("Field_Id") if "Field_Id" in display_cols else gdf[display_cols],
            use_container_width=True,
            hide_index=True,
        )

        # Delete field
        with st.expander("🗑️  Remove a field"):
            del_id = st.selectbox(
                "Select Field to delete",
                options=sorted(gdf["Field_Id"].tolist()),
                format_func=lambda x: f"Field {x} – {gdf[gdf['Field_Id']==x]['Crop_Type'].values[0] if 'Crop_Type' in gdf.columns else '?'}",
            )
            if st.button("🗑️  Delete selected field", type="secondary"):
                _delete_field(del_id)
                st.success(f"Field #{del_id} removed.")
                st.rerun()


# ── Private helpers ───────────────────────────────────────────────────────────

def _load_fields() -> gpd.GeoDataFrame:
    path = Path(FIELDS_PATH)
    if not path.exists() or path.stat().st_size < 10:
        return gpd.GeoDataFrame(columns=["Field_Id","Crop_Type","Season","geometry"], crs="EPSG:4326")
    try:
        gdf = gpd.read_file(path)
        if "Field_Id" in gdf.columns:
            gdf["Field_Id"] = gdf["Field_Id"].astype(int)
        return gdf
    except Exception:
        return gpd.GeoDataFrame(columns=["Field_Id","Crop_Type","Season","geometry"], crs="EPSG:4326")


def _extract_coordinates(map_result: dict, manual_text: str) -> list[list[float]]:
    """Try to get polygon coordinates from drawn shape first, then manual input."""

    # ── From drawn map polygon ────────────────────────────────────────────────
    if map_result:
        # Check all_drawings first
        for drawing in (map_result.get("all_drawings") or []):
            geom = drawing.get("geometry", {})
            gtype = geom.get("type", "")
            coords = geom.get("coordinates", [])
            if gtype == "Polygon" and coords:
                return coords[0]
            if gtype == "Rectangle" and coords:
                return coords[0]

        # Also check last_active_drawing (streamlit-folium returns this)
        last = map_result.get("last_active_drawing") or {}
        geom = last.get("geometry", {})
        gtype = geom.get("type", "")
        coords = geom.get("coordinates", [])
        if gtype in ("Polygon", "Rectangle") and coords:
            return coords[0]

    # ── From manual text input ────────────────────────────────────────────────
    if manual_text and manual_text.strip():
        coords = []
        for line in manual_text.strip().splitlines():
            line = line.strip().replace(";", ",")
            if not line:
                continue
            try:
                parts = line.split(",")
                lon, lat = float(parts[0].strip()), float(parts[1].strip())
                coords.append([lon, lat])
            except (ValueError, IndexError):
                continue
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])  # close ring
        return coords

    return []


def _save_field(
    coords: list,
    crop_type: str,
    season: str,
    soil_type: str,
    client_name: str,
    notes: str,
) -> int:
    """Append new field to fields.geojson and return the new Field_Id."""
    path = Path(FIELDS_PATH)

    # Load existing
    if path.exists() and path.stat().st_size > 10:
        with open(path, encoding="utf-8") as f:
            geojson = json.load(f)
        features = geojson.get("features", [])
    else:
        features = []

    # Generate new ID
    existing_ids = [
        int(f["properties"].get("Field_Id", 0))
        for f in features
        if f.get("properties")
    ]
    new_id = max(existing_ids, default=0) + 1

    # Build new feature
    new_feature = {
        "type": "Feature",
        "properties": {
            "Field_Id":   new_id,
            "Crop_Type":  crop_type,
            "Season":     season,
            "Soil_Type":  soil_type,
            "Client":     client_name,
            "Notes":      notes,
            "LastUpdate": datetime.now().isoformat(),
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords],
        },
    }

    features.append(new_feature)

    # Write back
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, indent=2)

    return new_id


def _delete_field(field_id: int):
    path = Path(FIELDS_PATH)
    if not path.exists():
        return
    with open(path, encoding="utf-8") as f:
        geojson = json.load(f)
    geojson["features"] = [
        feat for feat in geojson["features"]
        if int(feat["properties"].get("Field_Id", -1)) != field_id
    ]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
