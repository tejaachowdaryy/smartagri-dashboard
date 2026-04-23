"""
ui/home.py
===========
Dashboard home page – summary cards, field overview map, quick-stats.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modules import satellite_monitoring


# ── colour palette (matches global CSS vars) ─────────────────────────────────
C_GREEN  = "#2ecc71"
C_GOLD   = "#f0c040"
C_SOIL   = "#8b5e3c"
C_SKY    = "#3a9ad9"
C_DARK   = "#0d2b1a"
C_CARD   = "#112214"
C_BORDER = "#1e3d28"


def app():
    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style='padding: 8px 0 28px 0;'>
            <div style='font-family:Syne,sans-serif; font-size:2.2rem;
                        font-weight:800; color:#2ecc71; letter-spacing:-0.5px;'>
                🌾 SmartAgri Intelligence Platform
            </div>
            <div style='color:#8ab89a; font-size:0.95rem; margin-top:4px;'>
                Unified Crop Recommendation · Satellite Monitoring · Field Analytics
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load fields ───────────────────────────────────────────────────────────
    gdf = satellite_monitoring.load_fields("./data/fields.geojson")

    # ── KPI cards ─────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Fields", len(gdf), delta=None)
    with col2:
        crop_types = gdf["Crop_Type"].nunique() if "Crop_Type" in gdf.columns else "—"
        st.metric("Crop Types", crop_types)
    with col3:
        seasons = gdf["Season"].nunique() if "Season" in gdf.columns else "—"
        st.metric("Seasons", seasons)
    with col4:
        st.metric("Data Source", "GEE / Demo")

    st.markdown("<hr style='border-color:#1e3d28; margin: 20px 0;'>", unsafe_allow_html=True)

    # ── Two columns: map + charts ─────────────────────────────────────────────
    left, right = st.columns([3, 2], gap="large")

    with left:
        st.markdown(
            "<div style='font-family:Syne,sans-serif; font-size:1.1rem;"
            " font-weight:700; color:#e8f5ec; margin-bottom:12px;'>"
            "📍 Field Boundaries Overview</div>",
            unsafe_allow_html=True,
        )
        _render_field_map(gdf)

    with right:
        st.markdown(
            "<div style='font-family:Syne,sans-serif; font-size:1.1rem;"
            " font-weight:700; color:#e8f5ec; margin-bottom:12px;'>"
            "🌾 Crop Distribution</div>",
            unsafe_allow_html=True,
        )
        _render_crop_pie(gdf)

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<div style='font-family:Syne,sans-serif; font-size:1.1rem;"
            " font-weight:700; color:#e8f5ec; margin-bottom:12px;'>"
            "📅 Season Breakdown</div>",
            unsafe_allow_html=True,
        )
        _render_season_bar(gdf)

    st.markdown("<hr style='border-color:#1e3d28; margin: 24px 0;'>", unsafe_allow_html=True)

    # ── Field summary table ───────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:Syne,sans-serif; font-size:1.1rem;"
        " font-weight:700; color:#e8f5ec; margin-bottom:12px;'>"
        "📋 Field Registry</div>",
        unsafe_allow_html=True,
    )
    _render_field_table(gdf)

    # ── Quick-start guide ─────────────────────────────────────────────────────
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    with st.expander("🚀  Quick-Start Guide", expanded=False):
        st.markdown(
            """
            | Step | Where | What to do |
            |------|-------|-----------|
            | 1 | **Crop Recommendation** | Enter soil & climate parameters → get ML crop advice |
            | 2 | **Satellite Monitoring** | Select a field & date → view NDVI / LAI / True Color |
            | 3 | **Field Analytics**      | Explore time-series vegetation trends per field |

            **GEE Setup** — edit `config.yaml` and set `use_demo_mode: false`, then fill in
            your `service_account` and `key_file` paths (or run `earthengine authenticate`
            in your terminal before launching the app).
            """,
            unsafe_allow_html=True,
        )


# ── Private render helpers ────────────────────────────────────────────────────

def _render_field_map(gdf):
    if gdf.empty:
        st.info("No field data available.")
        return

    center = [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()]
    m = folium.Map(
        location=center,
        zoom_start=12,
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Satellite Hybrid",
    )

    colors = ["#2ecc71", "#f0c040", "#3a9ad9", "#e74c3c", "#9b59b6", "#e67e22", "#1abc9c"]

    crop_color = {}
    for i, crop in enumerate(gdf["Crop_Type"].unique() if "Crop_Type" in gdf.columns else []):
        crop_color[crop] = colors[i % len(colors)]

    for _, row in gdf.iterrows():
        crop = row.get("Crop_Type", "Unknown")
        fid  = row.get("Field_Id", "?")
        color = crop_color.get(crop, "#2ecc71")

        folium.GeoJson(
            row["geometry"].__geo_interface__,
            style_function=lambda _, c=color: {
                "fillColor": c,
                "color": "white",
                "weight": 2,
                "fillOpacity": 0.45,
            },
            tooltip=folium.Tooltip(
                f"<b>Field {fid}</b><br>Crop: {crop}<br>Season: {row.get('Season','?')}",
                sticky=True,
            ),
        ).add_to(m)

    st_folium(m, height=380, use_container_width=True)


def _render_crop_pie(gdf):
    if "Crop_Type" not in gdf.columns or gdf.empty:
        st.info("No crop data.")
        return

    counts = gdf["Crop_Type"].value_counts().reset_index()
    counts.columns = ["Crop", "Count"]

    fig = px.pie(
        counts,
        values="Count",
        names="Crop",
        color_discrete_sequence=["#2ecc71","#f0c040","#3a9ad9","#e74c3c","#9b59b6","#e67e22"],
        hole=0.5,
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e8f5ec",
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        legend=dict(font=dict(color="#8ab89a", size=11)),
        height=200,
    )
    fig.update_traces(textfont_color="#e8f5ec")
    st.plotly_chart(fig, use_container_width=True)


def _render_season_bar(gdf):
    if "Season" not in gdf.columns or gdf.empty:
        return
    counts = gdf["Season"].value_counts().reset_index()
    counts.columns = ["Season", "Count"]
    fig = px.bar(
        counts,
        x="Season",
        y="Count",
        color="Count",
        color_continuous_scale=[[0, "#1a4a2e"], [1, "#2ecc71"]],
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e8f5ec",
        margin=dict(t=10, b=10, l=10, r=10),
        height=160,
        coloraxis_showscale=False,
        xaxis=dict(gridcolor="#1e3d28"),
        yaxis=dict(gridcolor="#1e3d28"),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_field_table(gdf):
    if gdf.empty:
        st.info("No fields loaded.")
        return

    display_cols = [c for c in ["Field_Id", "Crop_Type", "Season", "LastUpdate"] if c in gdf.columns]
    st.dataframe(
        gdf[display_cols].sort_values("Field_Id") if "Field_Id" in display_cols else gdf[display_cols],
        use_container_width=True,
        hide_index=True,
    )
