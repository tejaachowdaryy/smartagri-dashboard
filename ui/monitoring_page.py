"""
ui/monitoring_page.py
======================
Satellite Crop Monitoring UI – field selector, date picker,
NDVI / LAI / True Color maps, and time-series chart.
Uses GEE when authenticated; falls back to demo data automatically.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import yaml
from pathlib import Path

from modules import satellite_monitoring, gee_utils

C_GREEN = "#2ecc71"
C_GOLD  = "#f0c040"
C_DARK  = "#0d2b1a"


# ── GEE init (once per session) ───────────────────────────────────────────────

@st.cache_resource(show_spinner=False, ttl=3600)
def _init_gee() -> bool:
    cfg_path = Path("./config.yaml")
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        gee_cfg = cfg.get("GEE", {})
        if gee_cfg.get("use_demo_mode", True):
            return False
        sa      = gee_cfg.get("service_account", "")
        key     = gee_cfg.get("key_file", "")
        project = gee_cfg.get("project", "")
        return gee_utils.initialise_gee(sa, key, project)
    return False


def app():
    st.markdown(
        """
        <div style='padding: 8px 0 24px 0;'>
            <div style='font-family:Syne,sans-serif; font-size:2rem;
                        font-weight:800; color:#2ecc71;'>
                🛰️ Satellite Crop Monitoring
            </div>
            <div style='color:#8ab89a; font-size:0.9rem; margin-top:4px;'>
                Sentinel-2 imagery via Google Earth Engine · NDVI · LAI · True Color
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    gee_ok = _init_gee()

    # Status badge
    mode_label = "🟢 GEE Connected — Real Sentinel-2 data" if gee_ok else "🟡 Demo Mode (synthetic data)"
    mode_color = C_GREEN if gee_ok else C_GOLD
    st.markdown(
        f"<div style='font-size:0.78rem; color:{mode_color}; margin-bottom:4px;'>"
        f"{mode_label}</div>",
        unsafe_allow_html=True,
    )
    if not gee_ok:
        # Show actionable GEE setup steps
        with st.expander("⚙️ How to enable real GEE data", expanded=False):
            st.markdown("""
**Step 1** — Activate your venv and authenticate:
```bash
venv\\Scripts\\activate
earthengine authenticate
```
**Step 2** — Verify it works:
```bash
python -c "import ee; ee.Initialize(); print('GEE OK')"
```
**Step 3** — Edit `config.yaml`:
```yaml
GEE:
  use_demo_mode: false
  service_account: ""
  key_file: ""
```
**Step 4** — Restart the app:
```bash
streamlit run app.py
```
""")

    # ── Load fields ───────────────────────────────────────────────────────────
    gdf = satellite_monitoring.load_fields("./data/fields.geojson")
    if gdf.empty:
        st.warning("No field data found. Please add fields via the Field Analytics page.")
        return

    field_options = {
        f"Field {row['Field_Id']} – {row.get('Crop_Type','?')}": row["Field_Id"]
        for _, row in gdf.iterrows()
    }

    # ── Sidebar controls ──────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:Syne,sans-serif; font-weight:700;"
        " color:#e8f5ec; margin-bottom:10px;'>📡 Observation Controls</div>",
        unsafe_allow_html=True,
    )

    ctrl1, ctrl2, ctrl3 = st.columns(3)
    with ctrl1:
        selected_label = st.selectbox("🌾 Select Field", list(field_options.keys()))
        field_id = field_options[selected_label]
    with ctrl2:
        year = st.selectbox("📅 Year", list(range(2026, 2017, -1)), index=3)
    with ctrl3:
        metric = st.selectbox("📊 Vegetation Index", ["NDVI", "LAI", "True Color"])

    # ── Fetch available dates ─────────────────────────────────────────────────
    with st.spinner("Fetching available satellite dates…"):
        dates = satellite_monitoring.get_available_dates(gdf, field_id, year, gee_ok)

    if not dates:
        st.warning("No satellite imagery available for this field/year combination.")
        return

    selected_date = st.select_slider(
        "🗓️  Select Date",
        options=dates,
        value=dates[len(dates) // 2],
    )

    st.markdown("<hr style='border-color:#1e3d28; margin:20px 0;'>", unsafe_allow_html=True)

    # ── Map + Index panel ─────────────────────────────────────────────────────
    map_col, idx_col = st.columns([3, 2], gap="large")

    with map_col:
        st.markdown(
            "<div style='font-family:Syne,sans-serif; font-weight:700;"
            " color:#e8f5ec; margin-bottom:10px;'>🗺️ Field Boundary Map</div>",
            unsafe_allow_html=True,
        )
        _render_field_map(gdf, field_id)

    with idx_col:
        st.markdown(
            f"<div style='font-family:Syne,sans-serif; font-weight:700;"
            f" color:#e8f5ec; margin-bottom:10px;'>🌿 {metric} Map – {selected_date}</div>",
            unsafe_allow_html=True,
        )
        with st.spinner(f"Loading {metric} data…"):
            try:
                _render_index_map(gdf, field_id, selected_date, metric, gee_ok)
            except Exception as _e:
                st.error(f"Could not render {metric} map: {_e}")

    st.markdown("<hr style='border-color:#1e3d28; margin:24px 0;'>", unsafe_allow_html=True)

    # ── Summary metrics ───────────────────────────────────────────────────────
    _render_summary_metrics(gdf, field_id, selected_date, gee_ok)

    st.markdown("<hr style='border-color:#1e3d28; margin:24px 0;'>", unsafe_allow_html=True)

    # ── Time-series chart ─────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:Syne,sans-serif; font-weight:700;"
        " color:#e8f5ec; margin-bottom:10px;'>📈 Seasonal Vegetation Time-Series</div>",
        unsafe_allow_html=True,
    )
    with st.spinner("Building time-series…"):
        ts = satellite_monitoring.get_timeseries(gdf, field_id, year, dates, gee_ok)
        _render_timeseries(ts, selected_date)


# ── Private render helpers ────────────────────────────────────────────────────

def _render_field_map(gdf, active_field_id):
    row = gdf[gdf["Field_Id"] == active_field_id].iloc[0]
    cent = row["geometry"].centroid
    m = folium.Map(
        location=[cent.y, cent.x],
        zoom_start=14,
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google Satellite Hybrid",
    )

    for _, r in gdf.iterrows():
        is_active = r["Field_Id"] == active_field_id
        folium.GeoJson(
            r["geometry"].__geo_interface__,
            style_function=lambda _, a=is_active: {
                "fillColor": "#2ecc71" if a else "#8ab89a",
                "color": "white" if a else "#4a7a5a",
                "weight": 3 if a else 1,
                "fillOpacity": 0.5 if a else 0.2,
            },
            tooltip=folium.Tooltip(
                f"<b>Field {r['Field_Id']}</b> – {r.get('Crop_Type','?')}",
                sticky=True,
            ),
        ).add_to(m)

    st_folium(m, height=320, use_container_width=True)


def _render_index_map(gdf, field_id, date, metric, gee_ok):
    if metric == "True Color":
        img = satellite_monitoring.get_true_color(gdf, field_id, date, gee_ok, size=128)
        st.image(img, caption=f"True Color – {date}", use_container_width=True)
        return

    if metric == "NDVI":
        arr = satellite_monitoring.get_ndvi_map(gdf, field_id, date, gee_ok, size=64)
        colorscale = "RdYlGn"
        zmin, zmax = -0.2, 1.0
        label = "NDVI"
    else:  # LAI
        arr = satellite_monitoring.get_lai_map(gdf, field_id, date, gee_ok, size=64)
        colorscale = "Greens"
        zmin, zmax = 0.0, 6.0
        label = "LAI"

    # Ensure 2D array — GEE may return flat list
    arr = np.array(arr, dtype=np.float32)
    if arr.ndim == 1:
        side = int(np.sqrt(len(arr)))
        arr  = arr[:side*side].reshape(side, side)
    arr = np.nan_to_num(arr, nan=0.0)

    fig = go.Figure(
        go.Heatmap(
            z=arr,
            colorscale=colorscale,
            zmin=zmin,
            zmax=zmax,
            colorbar=dict(
                title=label,
                title_font=dict(color="#e8f5ec"),
                tickfont=dict(color="#e8f5ec"),
                bgcolor="rgba(0,0,0,0)",
            ),
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=10, l=10, r=10),
        height=300,
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis=dict(showticklabels=False, showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_summary_metrics(gdf, field_id, date, gee_ok):
    ndvi_arr = satellite_monitoring.get_ndvi_map(gdf, field_id, date, gee_ok)
    lai_arr  = satellite_monitoring.get_lai_map(gdf, field_id, date, gee_ok)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean NDVI",  f"{float(np.mean(ndvi_arr)):.3f}")
    c2.metric("Max NDVI",   f"{float(np.max(ndvi_arr)):.3f}")
    c3.metric("Mean LAI",   f"{float(np.mean(lai_arr)):.2f}")
    c4.metric("Max LAI",    f"{float(np.max(lai_arr)):.2f}")

    # NDVI health interpretation
    mean_ndvi = float(np.mean(ndvi_arr))
    if mean_ndvi >= 0.6:
        health, color = "🟢 Excellent vegetation health", C_GREEN
    elif mean_ndvi >= 0.4:
        health, color = "🟡 Good vegetation health", C_GOLD
    elif mean_ndvi >= 0.2:
        health, color = "🟠 Moderate / stressed vegetation", "#e67e22"
    else:
        health, color = "🔴 Sparse or stressed vegetation", "#e74c3c"

    st.markdown(
        f"<div style='margin-top:8px; font-size:0.9rem; color:{color};'>{health}</div>",
        unsafe_allow_html=True,
    )


def _render_timeseries(ts: dict, selected_date: str):
    dates  = ts["dates"]
    ndvi   = ts["ndvi"]
    lai    = ts["lai"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=dates, y=ndvi,
        name="NDVI",
        mode="lines+markers",
        line=dict(color=C_GREEN, width=2.5),
        marker=dict(size=6, color=C_GREEN),
        fill="tozeroy",
        fillcolor="rgba(46,204,113,0.08)",
    ))

    fig.add_trace(go.Scatter(
        x=dates, y=lai,
        name="LAI",
        mode="lines+markers",
        line=dict(color=C_GOLD, width=2, dash="dot"),
        marker=dict(size=6, color=C_GOLD),
        yaxis="y2",
    ))

    # Highlight selected date (use add_shape for Plotly < 5.12 compatibility)
    if selected_date in dates:
        fig.add_shape(
            type="line",
            x0=selected_date, x1=selected_date,
            y0=0, y1=1,
            xref="x", yref="paper",
            line=dict(color="#3a9ad9", width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=selected_date, y=1,
            xref="x", yref="paper",
            text=f"📍 {selected_date}",
            showarrow=False,
            font=dict(color="#3a9ad9", size=11),
            yanchor="bottom",
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e8f5ec",
        legend=dict(font=dict(color="#8ab89a"), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=10, b=10, l=10, r=10),
        height=300,
        hovermode="x unified",
        xaxis=dict(gridcolor="#1e3d28", title="Date"),
        yaxis=dict(
            gridcolor="#1e3d28",
            title="NDVI",
            range=[-0.1, 1.0],
            title_font=dict(color=C_GREEN),
        ),
        yaxis2=dict(
            title="LAI",
            overlaying="y",
            side="right",
            range=[0, 6],
            title_font=dict(color=C_GOLD),
            tickfont=dict(color=C_GOLD),
            showgrid=False,
        ),
    )

    st.plotly_chart(fig, use_container_width=True)
