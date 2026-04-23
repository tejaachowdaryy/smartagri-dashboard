"""
ui/analytics_page.py
=====================
Field Analytics:
  - Multi-field NDVI / LAI comparison
  - Field health leaderboard
  - NDVI box plot distribution
  - Yield estimation from NDVI / LAI metrics
  - Per-field fertilizer & agronomic tips
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

from modules import satellite_monitoring

C_GREEN = "#2ecc71"
C_GOLD  = "#f0c040"
C_SKY   = "#3a9ad9"
C_RED   = "#e74c3c"
C_ORG   = "#e67e22"
PALETTE = [C_GREEN, C_GOLD, C_SKY, C_RED, "#9b59b6", C_ORG, "#1abc9c"]

# ── Crop knowledge base ────────────────────────────────────────────────────────
CROP_KB = {
    "Wheat": {
        "yield_base": 3.5,
        "fertilizers": {
            "Nitrogen (N)":   "120-150 kg/ha — apply in 3 splits: basal, tillering, flag-leaf",
            "Phosphorus (P)": "60-80 kg/ha — apply fully as basal dose",
            "Potassium (K)":  "40-60 kg/ha — apply fully as basal dose",
            "Zinc (ZnSO4)":   "25 kg/ha if deficient — apply once before sowing",
        },
        "tips": [
            "Ensure soil pH 6.0-7.5 for optimum nutrient uptake.",
            "Use certified seed varieties resistant to rust disease.",
            "Irrigate at crown root initiation, tillering, and grain filling stages.",
            "Apply herbicide 30-35 days after sowing to control weeds.",
            "Monitor for aphids and apply neem-based pesticide if detected early.",
        ],
    },
    "Maize": {
        "yield_base": 5.0,
        "fertilizers": {
            "Nitrogen (N)":   "150-180 kg/ha — apply 1/3 basal, 1/3 at knee-high, 1/3 tasselling",
            "Phosphorus (P)": "70-90 kg/ha — fully as basal",
            "Potassium (K)":  "60-80 kg/ha — fully as basal",
            "Boron (B)":      "1-2 kg/ha foliar spray at tasselling for better grain set",
        },
        "tips": [
            "Optimal plant density: 65,000-75,000 plants/ha.",
            "Irrigate at critical stages: knee-high, tasselling, silking, grain fill.",
            "Intercrop with legumes to improve soil nitrogen.",
            "Watch for fall armyworm — inspect whorls regularly.",
            "Harvest when grain moisture is below 20% to reduce storage loss.",
        ],
    },
    "Sorghum": {
        "yield_base": 2.8,
        "fertilizers": {
            "Nitrogen (N)":   "80-100 kg/ha — split equally at sowing and 30 DAS",
            "Phosphorus (P)": "40-60 kg/ha — fully at sowing",
            "Potassium (K)":  "40 kg/ha — fully at sowing",
        },
        "tips": [
            "Sorghum tolerates drought but yields best with 500-750 mm rainfall.",
            "Thin to 1 plant/hill at 10 DAS for optimum stand.",
            "Control striga weed aggressively — it severely reduces yield.",
            "Apply gypsum in sodic/alkaline soils to improve structure.",
            "Post-harvest dry heads to 12-13% moisture before storage.",
        ],
    },
    "Banana": {
        "yield_base": 35.0,
        "fertilizers": {
            "Nitrogen (N)":   "200-300 g/plant/year — apply in 4-6 monthly splits",
            "Phosphorus (P)": "100 g/plant/year — apply at planting and 4 months",
            "Potassium (K)":  "300-400 g/plant/year — most critical nutrient for banana",
            "Magnesium":      "50-75 g/plant/year — prevents inter-veinal chlorosis",
        },
        "tips": [
            "Maintain soil moisture at field capacity — drip irrigation preferred.",
            "De-sucker to 1 mother + 1 ratoon to maximise bunch size.",
            "Apply mulch 30-40 cm deep to conserve moisture and add organic matter.",
            "Control Panama wilt by using resistant varieties (Cavendish, FHIA).",
            "Bunch cover with blue polyethylene bags improves size and skin quality.",
        ],
    },
    "Coconut": {
        "yield_base": 12.0,
        "fertilizers": {
            "Nitrogen (N)":   "500 g/palm/year — apply in 2 splits (June, December)",
            "Phosphorus (P)": "320 g/palm/year — apply as single dose",
            "Potassium (K)":  "1200 g/palm/year — most critical; apply in 2 splits",
            "Chloride":       "Potassium chloride preferred over sulphate form",
        },
        "tips": [
            "Basin irrigation at 3-4 day intervals in dry months is essential.",
            "Apply green manure / organic compost 25-50 kg/palm/year.",
            "Button shedding can be reduced by boron foliar spray.",
            "Control rhinoceros beetle using pheromone traps.",
            "Intercrop with banana, cocoa or pepper for additional income.",
        ],
    },
    "Arecanut": {
        "yield_base": 2.5,
        "fertilizers": {
            "Nitrogen (N)":   "100 g/palm/year — split in 3 doses",
            "Phosphorus (P)": "40 g/palm/year",
            "Potassium (K)":  "140 g/palm/year",
            "Magnesium":      "Apply dolomite 500 g/palm if deficiency seen",
        },
        "tips": [
            "Provide 50% shade in initial years using silver oak or coconut.",
            "Irrigate every 3-4 days during summer; avoid water stagnation.",
            "Apply 25-30 kg compost/FYM per palm annually.",
            "Control Koleroga (fruit rot) with Bordeaux mixture 1% at onset of monsoon.",
            "Harvest bunches at yellow-ripe stage for maximum value.",
        ],
    },
    "Groundnut": {
        "yield_base": 2.2,
        "fertilizers": {
            "Nitrogen (N)":   "20-25 kg/ha — only as starter dose (nodules fix rest)",
            "Phosphorus (P)": "40-50 kg/ha — full basal dose",
            "Potassium (K)":  "40 kg/ha — full basal dose",
            "Gypsum":         "500 kg/ha — apply at pegging stage for pod filling",
            "Boron":          "1 kg/ha foliar spray at flowering",
        },
        "tips": [
            "Inoculate seed with Rhizobium before sowing for nitrogen fixation.",
            "Optimal pH 6.0-6.5; apply lime if soil is acidic.",
            "Earthing up at 30 DAS promotes peg entry and pod development.",
            "Control leaf spot and rust with Mancozeb 0.2% spray at 45 DAS.",
            "Harvest when 70-75% of pods show darkening inside the shell.",
        ],
    },
    "Cotton(lint)": {
        "yield_base": 1.8,
        "fertilizers": {
            "Nitrogen (N)":   "150-180 kg/ha — split into 4 doses through the season",
            "Phosphorus (P)": "60-80 kg/ha — fully at sowing",
            "Potassium (K)":  "80-100 kg/ha — improves fibre quality",
            "Sulphur":        "20-30 kg/ha — apply as gypsum with basal dose",
        },
        "tips": [
            "Use Bt-cotton hybrids to reduce bollworm pressure.",
            "Deploy pheromone traps (5/ha) to monitor pink bollworm.",
            "Irrigate at square formation, flowering, and boll development.",
            "Topping at 75 DAS limits vegetative growth and boosts boll retention.",
            "Apply ethephon 200 ppm before harvest to synchronise boll opening.",
        ],
    },
    "Rice": {
        "yield_base": 4.5,
        "fertilizers": {
            "Nitrogen (N)":   "100-120 kg/ha — 50% basal, 25% at tillering, 25% at panicle initiation",
            "Phosphorus (P)": "50-60 kg/ha — fully as basal",
            "Potassium (K)":  "50-60 kg/ha — split between basal and panicle initiation",
            "Zinc (ZnSO4)":   "25 kg/ha — apply 1 week before transplanting",
        },
        "tips": [
            "Maintain 2-5 cm standing water during active tillering.",
            "Alternate wetting and drying (AWD) saves 30% water with minimal yield loss.",
            "Transplant at 20-25 days old seedlings for optimum tillering.",
            "Use System of Rice Intensification (SRI) to boost yield with less water.",
            "Control blast disease with Tricyclazole 0.06% at boot leaf stage.",
        ],
    },
    "Dry chillies": {
        "yield_base": 1.5,
        "fertilizers": {
            "Nitrogen (N)":   "120 kg/ha — in 4 splits through the crop period",
            "Phosphorus (P)": "60 kg/ha — fully basal",
            "Potassium (K)":  "50 kg/ha — split in 2 doses",
            "Calcium":        "Apply lime 500 kg/ha if pH < 5.5",
        },
        "tips": [
            "Raise nursery in raised beds; transplant 35-40 day old seedlings.",
            "Drip irrigation with fertigation improves yield by 40%.",
            "Apply mulch to conserve moisture and suppress weeds.",
            "Control thrips and mites — major vectors of leaf curl virus.",
            "Harvest when 80% fruits turn red; dry to 8-10% moisture.",
        ],
    },
    "Dry ginger": {
        "yield_base": 1.8,
        "fertilizers": {
            "Nitrogen (N)":   "75 kg/ha — split in 3 doses",
            "Phosphorus (P)": "50 kg/ha — fully as basal with organic matter",
            "Potassium (K)":  "75 kg/ha — split in 2 doses",
            "Organic matter": "25-30 t/ha compost or FYM before planting",
        },
        "tips": [
            "Plant rhizomes at 45x25 cm spacing after pre-sprouting.",
            "Mulch with green leaves 15 cm deep at planting and 45 DAS.",
            "Provide 50% shade in summer months using shade net.",
            "Control soft rot (Pythium) with Metalaxyl seed treatment.",
            "Harvest at 8-9 months when leaves turn yellow and dry.",
        ],
    },
}

_DEFAULT_KB = {
    "yield_base": 3.0,
    "fertilizers": {
        "Nitrogen (N)":   "80-120 kg/ha — apply in 2-3 splits",
        "Phosphorus (P)": "40-60 kg/ha — apply as basal dose",
        "Potassium (K)":  "40-60 kg/ha — apply as basal dose",
    },
    "tips": [
        "Conduct soil testing before every season for targeted fertilisation.",
        "Maintain soil organic carbon above 0.5% by adding compost.",
        "Follow integrated pest management (IPM) principles.",
        "Irrigate based on crop water requirement; avoid over-irrigation.",
        "Consult local agricultural extension officer for variety selection.",
    ],
}


def _estimate_yield(crop, mean_ndvi, max_ndvi, mean_lai):
    kb         = CROP_KB.get(str(crop).strip(), _DEFAULT_KB)
    base_yield = kb["yield_base"]
    ndvi_factor = min(mean_ndvi / 0.75, 1.3)
    lai_factor  = min(mean_lai  / 3.5,  1.3)
    combined    = 0.60 * ndvi_factor + 0.40 * lai_factor
    stress      = 1.0 if max_ndvi >= 0.55 else 0.80
    est         = round(base_yield * combined * stress, 2)
    pct         = round((est / base_yield) * 100, 1)
    if pct >= 85:   grade, gcol = "Excellent", C_GREEN
    elif pct >= 65: grade, gcol = "Good",      C_GOLD
    elif pct >= 45: grade, gcol = "Moderate",  C_ORG
    else:           grade, gcol = "Poor",       C_RED
    return {"crop": crop, "est_yield": est, "potential": base_yield,
            "pct": pct, "grade": grade, "gcol": gcol,
            "mean_ndvi": round(mean_ndvi,3), "mean_lai": round(mean_lai,2)}


def _get_crop(gdf, fid):
    if "Crop_Type" not in gdf.columns: return "Unknown"
    vals = gdf[gdf["Field_Id"] == fid]["Crop_Type"].values
    return str(vals[0]) if len(vals) else "Unknown"


def _section_title(t):
    return (f"<div style='font-family:Syne,sans-serif; font-weight:700;"
            f" color:#e8f5ec; margin-bottom:10px; font-size:1.05rem;'>{t}</div>")


def _dark_layout(fig, xl="", yl="", h=300):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color="#e8f5ec",
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#8ab89a")),
        margin=dict(t=10,b=10,l=10,r=10), height=h, hovermode="x unified",
        xaxis=dict(gridcolor="#1e3d28", title=xl),
        yaxis=dict(gridcolor="#1e3d28", title=yl),
    )


def _rgb(h):
    h = h.lstrip("#")
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


def app():
    st.markdown("""
        <div style='padding:8px 0 24px 0;'>
            <div style='font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:#2ecc71;'>
                📊 Field Analytics</div>
            <div style='color:#8ab89a;font-size:0.9rem;margin-top:4px;'>
                Vegetation trends · Yield estimation · Fertilizer & agronomic recommendations</div>
        </div>""", unsafe_allow_html=True)

    gdf = satellite_monitoring.load_fields("./data/fields.geojson")
    if gdf.empty:
        st.warning("No field data found. Add fields via the Add New Field page.")
        return

    c1,c2,c3 = st.columns(3)
    with c1:
        year = st.selectbox("📅 Analysis Year", list(range(2026, 2017, -1)), index=3)
    with c2:
        all_lbls = [f"Field {r['Field_Id']} - {r.get('Crop_Type','?')}" for _,r in gdf.iterrows()]
        sel_lbls = st.multiselect("🌾 Select Fields", all_lbls, default=all_lbls[:min(3,len(all_lbls))])
    with c3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        run = st.button("▶️  Run Analysis", use_container_width=True)

    if not run:
        st.markdown("""<div style='text-align:center;padding:60px 20px;color:#4a7a5a;'>
            <div style='font-size:3rem;'>📊</div>
            <div style='font-family:Syne,sans-serif;font-size:1.1rem;margin-top:12px;'>
            Select fields and click <b style='color:#2ecc71;'>Run Analysis</b></div></div>""",
            unsafe_allow_html=True)
        return
    if not sel_lbls:
        st.warning("Please select at least one field.")
        return

    field_ids = [int(l.split("-")[0].replace("Field","").strip()) for l in sel_lbls]
    gee_ok    = False

    all_ts = {}
    with st.spinner("Loading satellite data..."):
        for fid in field_ids:
            dates      = satellite_monitoring.get_available_dates(gdf, fid, year, gee_ok)
            ts         = satellite_monitoring.get_timeseries(gdf, fid, year, dates, gee_ok)
            all_ts[fid] = ts

    st.markdown("<hr style='border-color:#1e3d28;margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTION 1: NDVI comparison ─────────────────────────────────────────────
    st.markdown(_section_title("📈 Multi-Field NDVI Comparison"), unsafe_allow_html=True)
    fig = go.Figure()
    for i,fid in enumerate(field_ids):
        ts = all_ts[fid]; crop = _get_crop(gdf,fid)
        fig.add_trace(go.Scatter(x=ts["dates"],y=ts["ndvi"],name=f"Field {fid} ({crop})",
            mode="lines+markers",line=dict(color=PALETTE[i%len(PALETTE)],width=2),marker=dict(size=5)))
    _dark_layout(fig,"Date","NDVI",300)
    fig.update_layout(yaxis=dict(range=[-0.1,1.0],gridcolor="#1e3d28"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr style='border-color:#1e3d28;margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTION 2: LAI + Leaderboard ──────────────────────────────────────────
    l,r = st.columns(2,gap="large")
    with l:
        st.markdown(_section_title("🍃 LAI Seasonal Comparison"), unsafe_allow_html=True)
        fig2 = go.Figure()
        for i,fid in enumerate(field_ids):
            ts=all_ts[fid]; crop=_get_crop(gdf,fid); c=PALETTE[i%len(PALETTE)]
            fig2.add_trace(go.Scatter(x=ts["dates"],y=ts["lai"],name=f"Field {fid} ({crop})",
                mode="lines",line=dict(color=c,width=2),fill="tozeroy",
                fillcolor=f"rgba({_rgb(c)},0.05)"))
        _dark_layout(fig2,"Date","LAI",280)
        st.plotly_chart(fig2, use_container_width=True)
    with r:
        st.markdown(_section_title("🏆 Health Leaderboard"), unsafe_allow_html=True)
        rows=[]
        for fid in field_ids:
            ts=all_ts[fid]; crop=_get_crop(gdf,fid)
            mn=float(np.mean(ts["ndvi"])); mx=float(np.max(ts["ndvi"])); ml=float(np.mean(ts["lai"]))
            y=_estimate_yield(crop,mn,mx,ml)
            rows.append({"Field":f"Field {fid}","Crop":crop,"Mean NDVI":round(mn,3),
                         "Mean LAI":round(ml,2),"Est. Yield":f"{y['est_yield']} t/ha","Grade":y["grade"]})
        st.dataframe(pd.DataFrame(rows).sort_values("Mean NDVI",ascending=False).reset_index(drop=True),
                     use_container_width=True,hide_index=True,height=280)

    st.markdown("<hr style='border-color:#1e3d28;margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTION 3: Box plots ───────────────────────────────────────────────────
    st.markdown(_section_title("📦 NDVI Distribution per Field"), unsafe_allow_html=True)
    fig3=go.Figure()
    for i,fid in enumerate(field_ids):
        ts=all_ts[fid]; crop=_get_crop(gdf,fid); c=PALETTE[i%len(PALETTE)]
        fig3.add_trace(go.Box(y=ts["ndvi"],name=f"Field {fid} ({crop})",
            marker_color=c,line_color=c,fillcolor=f"rgba({_rgb(c)},0.15)"))
    _dark_layout(fig3,"","NDVI",280)
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("<hr style='border-color:#1e3d28;margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTION 4: Yield estimation ────────────────────────────────────────────
    st.markdown(_section_title("🌾 Yield Estimation from Satellite Metrics"), unsafe_allow_html=True)
    st.caption("Empirical model using NDVI + LAI. Validate with field samples.")

    ydata=[]
    for fid in field_ids:
        ts=all_ts[fid]; crop=_get_crop(gdf,fid)
        mn=float(np.mean(ts["ndvi"])); mx=float(np.max(ts["ndvi"])); ml=float(np.mean(ts["lai"]))
        y=_estimate_yield(crop,mn,mx,ml); y["fid"]=fid; ydata.append(y)

    # KPI cards
    kcols=st.columns(len(ydata))
    for i,y in enumerate(ydata):
        with kcols[i]:
            st.markdown(f"""
            <div style='background:#0d2b1a;border:1px solid {y["gcol"]};border-radius:12px;
                        padding:14px 16px;text-align:center;'>
                <div style='font-size:0.7rem;color:#8ab89a;letter-spacing:1px;
                            text-transform:uppercase;'>Field {y["fid"]}</div>
                <div style='font-family:Syne,sans-serif;font-size:1.5rem;
                            font-weight:800;color:{y["gcol"]};margin:4px 0;'>{y["est_yield"]} t/ha</div>
                <div style='font-size:0.75rem;color:#a8e6c0;'>{y["crop"]}</div>
                <div style='font-size:0.72rem;color:{y["gcol"]};margin-top:4px;
                            font-weight:700;'>{y["grade"]} · {y["pct"]}% of potential</div>
                <div style='font-size:0.68rem;color:#8ab89a;margin-top:6px;'>
                    NDVI {y["mean_ndvi"]} · LAI {y["mean_lai"]}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # Yield bar chart – estimated vs potential
    fig4=go.Figure()
    fig4.add_trace(go.Bar(name="Potential",x=[f"Field {y['fid']}" for y in ydata],
        y=[y["potential"] for y in ydata],
        marker_color="rgba(139,94,60,0.35)",marker_line_color="#8b5e3c",marker_line_width=1))
    fig4.add_trace(go.Bar(name="Estimated",x=[f"Field {y['fid']}" for y in ydata],
        y=[y["est_yield"] for y in ydata],
        marker_color=[y["gcol"] for y in ydata]))
    fig4.update_layout(barmode="overlay",paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",font_color="#e8f5ec",
        legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(color="#8ab89a")),
        margin=dict(t=10,b=10,l=10,r=10),height=280,
        xaxis=dict(gridcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor="#1e3d28",title="t / ha"))
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("<hr style='border-color:#1e3d28;margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTION 5: Fertilizer & Tips ──────────────────────────────────────────
    st.markdown(_section_title("💊 Fertilizer Schedule & Agronomic Tips"), unsafe_allow_html=True)

    for y in ydata:
        crop=y["crop"]; fid=y["fid"]
        kb=CROP_KB.get(str(crop).strip(), _DEFAULT_KB)
        if y["grade"]=="Poor":        urg,ucol="🔴 Immediate action needed",C_RED
        elif y["grade"]=="Moderate":  urg,ucol="🟠 Monitor closely",C_ORG
        elif y["grade"]=="Good":      urg,ucol="🟡 Minor improvements possible",C_GOLD
        else:                         urg,ucol="🟢 On track",C_GREEN

        with st.expander(f"🌾 Field {fid} — {crop}  |  {y['est_yield']} t/ha  |  {urg}",
                         expanded=(y["grade"] in ["Poor","Moderate"])):
            cf,ct=st.columns(2,gap="large")
            with cf:
                st.markdown(f"<div style='font-family:Syne,sans-serif;font-weight:700;"
                            f"color:{ucol};margin-bottom:10px;'>💊 Fertilizer Schedule</div>",
                            unsafe_allow_html=True)
                for nutrient,dose in kb["fertilizers"].items():
                    st.markdown(f"""
                    <div style='background:#0a1f0f;border-left:3px solid #1e3d28;
                                border-radius:6px;padding:10px 14px;margin-bottom:8px;'>
                        <div style='font-weight:700;color:#2ecc71;font-size:0.85rem;'>{nutrient}</div>
                        <div style='color:#a8e6c0;font-size:0.82rem;margin-top:3px;
                                    line-height:1.5;'>{dose}</div>
                    </div>""", unsafe_allow_html=True)
                if y["mean_ndvi"] < 0.35:
                    st.markdown("""
                    <div style='background:rgba(231,76,60,0.08);border-left:3px solid #e74c3c;
                                border-radius:6px;padding:10px 14px;margin-top:8px;'>
                        <div style='font-weight:700;color:#e74c3c;font-size:0.85rem;'>
                            Warning: Low NDVI — Urgent Foliar Action</div>
                        <div style='color:#e8f5ec;font-size:0.82rem;margin-top:3px;'>
                            Apply foliar spray of 2% Urea + 0.5% ZnSO4 immediately
                            to provide quick nitrogen and micronutrient boost.</div>
                    </div>""", unsafe_allow_html=True)
                elif y["mean_ndvi"] < 0.5:
                    st.markdown("""
                    <div style='background:rgba(240,192,64,0.08);border-left:3px solid #f0c040;
                                border-radius:6px;padding:10px 14px;margin-top:8px;'>
                        <div style='font-weight:700;color:#f0c040;font-size:0.85rem;'>
                            Tip: Apply Top-Dress Nitrogen</div>
                        <div style='color:#e8f5ec;font-size:0.82rem;margin-top:3px;'>
                            Apply next split dose of nitrogen fertilizer to improve
                            canopy density and push NDVI above 0.6.</div>
                    </div>""", unsafe_allow_html=True)
            with ct:
                st.markdown("<div style='font-family:Syne,sans-serif;font-weight:700;"
                            "color:#3a9ad9;margin-bottom:10px;'>🌱 Agronomic Tips</div>",
                            unsafe_allow_html=True)
                for tip in kb["tips"]:
                    st.markdown(f"""
                    <div style='display:flex;gap:10px;align-items:flex-start;margin-bottom:8px;'>
                        <span style='color:#2ecc71;font-size:1rem;margin-top:1px;'>✓</span>
                        <span style='color:#a8e6c0;font-size:0.83rem;line-height:1.55;'>{tip}</span>
                    </div>""", unsafe_allow_html=True)
                if y["mean_lai"] < 1.5:
                    st.markdown(f"""
                    <div style='background:rgba(231,76,60,0.08);border-left:3px solid #e74c3c;
                                border-radius:6px;padding:10px 14px;margin-top:8px;'>
                        <div style='font-weight:700;color:#e74c3c;font-size:0.85rem;'>
                            Low Leaf Area Index ({y["mean_lai"]})</div>
                        <div style='color:#e8f5ec;font-size:0.82rem;margin-top:3px;'>
                            Canopy cover is insufficient. Check for pest damage,
                            water stress or nutrient deficiency and address urgently.</div>
                    </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1e3d28;margin:20px 0;'>", unsafe_allow_html=True)

    # ── SECTION 6: Summary table ───────────────────────────────────────────────
    st.markdown(_section_title("📋 Full Summary Table"), unsafe_allow_html=True)
    st.dataframe(pd.DataFrame([{
        "Field": f"Field {y['fid']}", "Crop": y["crop"],
        "Mean NDVI": y["mean_ndvi"], "Mean LAI": y["mean_lai"],
        "Est. Yield (t/ha)": y["est_yield"], "Potential (t/ha)": y["potential"],
        "% of Potential": f"{y['pct']}%", "Grade": y["grade"],
    } for y in ydata]), use_container_width=True, hide_index=True)
