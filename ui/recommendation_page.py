"""
ui/recommendation_page.py
===========================
Crop Recommendation UI – takes soil / climate inputs and returns ML prediction
with confidence, top-3 alternatives, yield estimate, and feature importance.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from modules import crop_recommendation
from modules import weather as weather_mod

C_GREEN = "#2ecc71"
C_GOLD  = "#f0c040"
C_SKY   = "#3a9ad9"


def app():
    # ── Page header ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style='padding: 8px 0 24px 0;'>
            <div style='font-family:Syne,sans-serif; font-size:2rem;
                        font-weight:800; color:#2ecc71;'>
                🌱 Crop Recommendation Engine
            </div>
            <div style='color:#8ab89a; font-size:0.9rem; margin-top:4px;'>
                ML-powered recommendations using Random Forest (96.8 % accuracy)
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Load metadata ─────────────────────────────────────────────────────────
    meta = crop_recommendation.get_model_meta("./models")

    # ── Weather forecast panel ────────────────────────────────────────────────
    _render_weather_panel()

    st.markdown("<hr style='border-color:#1e3d28; margin:20px 0;'>", unsafe_allow_html=True)

    # ── Input form ────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:Syne,sans-serif; font-size:1.05rem;"
        " font-weight:700; color:#e8f5ec; margin-bottom:12px;'>"
        "⚙️  Enter Field Parameters</div>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        state = st.selectbox("🗺️  State / Region", meta["states"])
        soil  = st.selectbox("🪨  Soil Type", meta["soils"])
        season = st.selectbox("📅  Season", meta["seasons"])

    with col2:
        area = st.number_input(
            "📐  Field Area (hectares)", min_value=0.1, max_value=100_000.0,
            value=100.0, step=10.0,
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.info(
            "ℹ️  The model was trained on Indian agricultural census data "
            "(23,320 records). Predictions are most reliable for the crops "
            "and regions present in the training data."
        )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    run = st.button("🔍  Recommend Crop", use_container_width=True)

    st.markdown("<hr style='border-color:#1e3d28; margin:20px 0;'>", unsafe_allow_html=True)

    # ── Results ───────────────────────────────────────────────────────────────
    if run:
        with st.spinner("Running ML inference…"):
            result = crop_recommendation.predict_crop(state, soil, season, area, "./models")
            yield_r = crop_recommendation.predict_yield(state, result["crop"], season, soil, area, "./models")

        # Top recommendation banner
        confidence_pct = round(result["confidence"] * 100, 1)
        _confidence_color = C_GREEN if confidence_pct >= 60 else C_GOLD if confidence_pct >= 40 else "#e74c3c"

        st.markdown(
            f"""
            <div style='background: linear-gradient(135deg, #0d2b1a, #1a4a2e);
                        border: 1px solid #2ecc71; border-radius: 14px;
                        padding: 24px 28px; margin-bottom: 24px;'>
                <div style='font-size:0.75rem; color:#8ab89a; letter-spacing:2px;
                            text-transform:uppercase; font-family:Syne,sans-serif;'>
                    Top Recommendation
                </div>
                <div style='font-family:Syne,sans-serif; font-size:2.4rem;
                            font-weight:800; color:#2ecc71; margin: 6px 0;'>
                    🌾 {result["crop"]}
                </div>
                <div style='font-size:0.9rem; color:#a8e6c0;'>
                    Confidence: <span style='color:{_confidence_color};
                    font-weight:700; font-size:1.1rem;'>{confidence_pct}%</span>
                    &nbsp;·&nbsp; State: <b>{state}</b>
                    &nbsp;·&nbsp; Soil: <b>{soil}</b>
                    &nbsp;·&nbsp; Season: <b>{season}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Metric row
        c1, c2, c3 = st.columns(3)
        c1.metric("Recommended Crop", result["crop"])
        c2.metric("Yield / ha (est.)", f"{yield_r['yield_per_ha']:.2f} t/ha")
        c3.metric("Total Production (est.)", f"{yield_r['total_production']:,.0f} t")

        st.markdown("<hr style='border-color:#1e3d28; margin:20px 0;'>", unsafe_allow_html=True)

        # Two columns: top-3 + probability bar chart
        left, right = st.columns([1, 2], gap="large")

        with left:
            st.markdown(
                "<div style='font-family:Syne,sans-serif; font-weight:700;"
                " color:#e8f5ec; margin-bottom:10px;'>🥇 Top 3 Alternatives</div>",
                unsafe_allow_html=True,
            )
            medals = ["🥇", "🥈", "🥉"]
            for i, item in enumerate(result["top3"]):
                pct = round(item["prob"] * 100, 1)
                st.markdown(
                    f"""
                    <div style='background:#112214; border:1px solid #1e3d28;
                                border-radius:10px; padding:12px 16px; margin-bottom:8px;'>
                        <div style='font-family:Syne,sans-serif; font-weight:700;
                                    color:#e8f5ec;'>{medals[i]} {item["crop"]}</div>
                        <div style='font-size:0.8rem; color:#8ab89a; margin-top:4px;'>
                            Probability: <span style='color:#2ecc71;'>{pct}%</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with right:
            st.markdown(
                "<div style='font-family:Syne,sans-serif; font-weight:700;"
                " color:#e8f5ec; margin-bottom:10px;'>📊 Probability Distribution</div>",
                unsafe_allow_html=True,
            )
            prob_df = pd.DataFrame(
                list(result["all_probs"].items()), columns=["Crop", "Probability"]
            ).sort_values("Probability", ascending=True)

            fig = px.bar(
                prob_df,
                x="Probability",
                y="Crop",
                orientation="h",
                color="Probability",
                color_continuous_scale=[[0, "#1a4a2e"], [0.5, "#27ae60"], [1, "#2ecc71"]],
                text=prob_df["Probability"].apply(lambda v: f"{v*100:.1f}%"),
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font_color="#e8f5ec",
                coloraxis_showscale=False,
                margin=dict(t=10, b=10, l=10, r=20),
                height=260,
                xaxis=dict(gridcolor="#1e3d28", tickformat=".0%"),
                yaxis=dict(gridcolor="rgba(0,0,0,0)"),
            )
            fig.update_traces(textfont_color="#e8f5ec", textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("<hr style='border-color:#1e3d28; margin:20px 0;'>", unsafe_allow_html=True)

        # Feature importance
        st.markdown(
            "<div style='font-family:Syne,sans-serif; font-weight:700;"
            " color:#e8f5ec; margin-bottom:10px;'>🔬 Model Feature Importance</div>",
            unsafe_allow_html=True,
        )
        fi_df = crop_recommendation.get_feature_importance("./models")
        fig2 = px.bar(
            fi_df,
            x="feature",
            y="importance",
            color="importance",
            color_continuous_scale=[[0, "#1a4a2e"], [1, "#2ecc71"]],
            labels={"feature": "Feature", "importance": "Importance"},
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e8f5ec",
            coloraxis_showscale=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=240,
            xaxis=dict(gridcolor="#1e3d28"),
            yaxis=dict(gridcolor="#1e3d28"),
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Explanation card
        _explanation_card(result["crop"], soil, season, state)

    else:
        # Idle state placeholder
        st.markdown(
            """
            <div style='text-align:center; padding:60px 20px; color:#4a7a5a;'>
                <div style='font-size:3rem; margin-bottom:12px;'>🌱</div>
                <div style='font-family:Syne,sans-serif; font-size:1.1rem;'>
                    Fill in the field parameters above and click
                    <b style='color:#2ecc71;'>Recommend Crop</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ── Private helpers ───────────────────────────────────────────────────────────

def _explanation_card(crop: str, soil: str, season: str, state: str):
    tips = {
        "Arecanut":     "Arecanut thrives in laterite soils with well-distributed rainfall. Ensure proper drainage and shade management.",
        "Banana":       "Banana requires deep, well-drained clayey loam soil. Regular irrigation and potassium-rich fertilisation are key.",
        "Coconut":      "Coconut is well-suited to coastal sandy soils with high humidity. Regular irrigation boosts nut yield significantly.",
        "Cotton(lint)": "Cotton grows best in black (regur) soil with moderate rainfall. Requires good pest management during boll formation.",
        "Dry chillies": "Dry chillies perform well in loamy soils. Avoid water-logging; drip irrigation is recommended.",
        "Dry ginger":   "Dry ginger prefers well-drained loamy soil rich in organic matter. Intercropping with coconut is a common practice.",
        "Groundnut":    "Groundnut thrives in sandy loam soil with moderate moisture. It fixes atmospheric nitrogen, benefiting subsequent crops.",
    }
    tip = tips.get(crop, f"{crop} is suitable for the selected soil and climatic conditions. Follow local extension advisory for best practices.")

    st.markdown(
        f"""
        <div style='background:#0a1f0f; border-left: 3px solid #2ecc71;
                    border-radius: 8px; padding: 16px 20px; margin-top: 8px;'>
            <div style='font-family:Syne,sans-serif; font-weight:700;
                        color:#2ecc71; margin-bottom:6px;'>
                💡 Agronomic Notes – {crop}
            </div>
            <div style='color:#a8e6c0; font-size:0.9rem; line-height:1.6;'>
                {tip}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Weather panel ─────────────────────────────────────────────────────────────

def _render_weather_panel():
    import plotly.graph_objects as go

    st.markdown(
        "<div style=\'font-family:Syne,sans-serif; font-size:1.05rem;"
        " font-weight:700; color:#e8f5ec; margin-bottom:10px;\'>"
        "🌤️  Live Weather Forecast</div>",
        unsafe_allow_html=True,
    )

    wc1, wc2 = st.columns([2, 3], gap="large")

    with wc1:
        city = st.text_input("📍 Location (city or leave blank for coordinates)",
                             placeholder="e.g. Khartoum, Sudan", key="wx_city")
        wlat = st.number_input("Latitude",  value=15.55, format="%.4f", key="wx_lat")
        wlon = st.number_input("Longitude", value=32.53, format="%.4f", key="wx_lon")
        fetch_wx = st.button("🔄 Get Weather", key="wx_btn", use_container_width=True)

    with wc2:
        if fetch_wx or "wx_data" in st.session_state:
            if fetch_wx:
                with st.spinner("Fetching weather…"):
                    if city.strip():
                        data = weather_mod.get_weather_by_city(city.strip())
                    else:
                        data = weather_mod.get_weather(wlat, wlon)
                st.session_state["wx_data"] = data

            data = st.session_state.get("wx_data")
            if not data:
                st.warning("Could not fetch weather. Check location name.")
                return

            cur = data["current"]
            st.markdown(
                f"""
                <div style=\'background:#0d2b1a; border:1px solid #1e3d28;
                            border-radius:12px; padding:16px 20px; margin-bottom:12px;\'>
                    <div style=\'font-size:0.7rem; color:#8ab89a; letter-spacing:2px;
                                text-transform:uppercase;\'>Current Conditions · {data["location"]}</div>
                    <div style=\'font-size:2rem; margin:6px 0;\'>{cur["icon"]} {cur["condition"]}</div>
                    <div style=\'display:flex; gap:24px; flex-wrap:wrap; margin-top:8px;\'>
                        <div><span style=\'color:#8ab89a; font-size:0.75rem;\'>TEMP</span>
                             <div style=\'color:#f0c040; font-weight:700; font-size:1.1rem;\'>{cur["temp"]}°C</div></div>
                        <div><span style=\'color:#8ab89a; font-size:0.75rem;\'>HUMIDITY</span>
                             <div style=\'color:#3a9ad9; font-weight:700; font-size:1.1rem;\'>{cur["humidity"]}%</div></div>
                        <div><span style=\'color:#8ab89a; font-size:0.75rem;\'>WIND</span>
                             <div style=\'color:#e8f5ec; font-weight:700; font-size:1.1rem;\'>{cur["windspeed"]} km/h</div></div>
                        <div><span style=\'color:#8ab89a; font-size:0.75rem;\'>RAINFALL</span>
                             <div style=\'color:#2ecc71; font-weight:700; font-size:1.1rem;\'>{cur["rainfall"]} mm</div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 7-day forecast strip
            fc = data["forecast"]
            fc_cols = st.columns(min(7, len(fc)))
            for i, day in enumerate(fc[:7]):
                with fc_cols[i]:
                    st.markdown(
                        f"""
                        <div style=\'background:#112214; border:1px solid #1e3d28;
                                    border-radius:8px; padding:8px 6px; text-align:center;\'>
                            <div style=\'font-size:0.65rem; color:#8ab89a;\'>{day["date"][5:]}</div>
                            <div style=\'font-size:1.3rem;\'>{day["icon"]}</div>
                            <div style=\'color:#f0c040; font-size:0.8rem; font-weight:700;\'>{day["max_temp"]}°</div>
                            <div style=\'color:#8ab89a; font-size:0.72rem;\'>{day["min_temp"]}°</div>
                            <div style=\'color:#3a9ad9; font-size:0.68rem;\'>{day["rainfall"]}mm</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            # Hourly temp chart
            if data.get("hourly_temp") and data.get("hourly_time"):
                fig = go.Figure(go.Scatter(
                    x=data["hourly_time"],
                    y=data["hourly_temp"],
                    mode="lines+markers",
                    line=dict(color="#f0c040", width=2),
                    marker=dict(size=4, color="#f0c040"),
                    fill="tozeroy",
                    fillcolor="rgba(240,192,64,0.06)",
                    name="Temp °C",
                ))
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font_color="#e8f5ec",
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=150,
                    xaxis=dict(gridcolor="#1e3d28", title="Hour"),
                    yaxis=dict(gridcolor="#1e3d28", title="°C"),
                    showlegend=False,
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.markdown(
                """
                <div style=\'text-align:center; padding:40px 20px; color:#4a7a5a;\'>
                    <div style=\'font-size:2.5rem;\'>🌤️</div>
                    <div style=\'font-size:0.9rem; margin-top:8px;\'>
                        Enter a location and click <b style=\'color:#2ecc71;\'>Get Weather</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
