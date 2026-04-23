"""
Smart Agriculture Dashboard
============================
Unified dashboard combining Crop Recommendation (ML) and
Satellite Crop Monitoring (GEE / demo fallback).

Run:
    streamlit run app.py
"""

import streamlit as st

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="SmartAgri Dashboard",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject global CSS theme ─────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }

    /* ── Dark agricultural theme ── */
    :root {
        --green-deep:   #0d2b1a;
        --green-mid:    #1a4a2e;
        --green-accent: #2ecc71;
        --green-light:  #a8e6c0;
        --gold:         #f0c040;
        --soil:         #8b5e3c;
        --sky:          #3a9ad9;
        --bg-card:      #112214;
        --bg-page:      #0a1f0f;
        --text-main:    #e8f5ec;
        --text-muted:   #8ab89a;
        --border:       #1e3d28;
    }

    .stApp {
        background: radial-gradient(ellipse at top left, #0d2b1a 0%, #060f08 60%);
        background-attachment: fixed;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a1f0f 0%, #061209 100%);
        border-right: 1px solid var(--border);
    }
    section[data-testid="stSidebar"] * { color: var(--text-main) !important; }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px !important;
        box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }
    [data-testid="metric-container"] label { color: var(--text-muted) !important; font-size: 0.78rem !important; }
    [data-testid="metric-container"] [data-testid="metric-value"] { color: var(--green-accent) !important; font-family: 'Syne', sans-serif !important; }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, var(--green-mid), var(--green-deep));
        color: var(--green-accent) !important;
        border: 1px solid var(--green-accent);
        border-radius: 8px;
        font-family: 'Syne', sans-serif;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: all 0.25s ease;
    }
    .stButton > button:hover {
        background: var(--green-accent);
        color: var(--green-deep) !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(46,204,113,0.3);
    }

    /* Select boxes, inputs */
    .stSelectbox > div, .stNumberInput > div { color: var(--text-main) !important; }

    /* Headers */
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; color: var(--text-main) !important; }

    /* Tab bar */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-card);
        border-radius: 10px;
        gap: 4px;
        padding: 4px;
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        color: var(--text-muted) !important;
        border-radius: 8px;
        font-family: 'Syne', sans-serif;
        font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] {
        background: var(--green-mid) !important;
        color: var(--green-accent) !important;
    }

    /* Divider */
    hr { border-color: var(--border) !important; }

    /* Streamlit default text */
    p, li, span { color: var(--text-main) !important; }
    .stMarkdown p { color: var(--text-main) !important; }

    /* Alert / info boxes */
    .stInfo  { background: rgba(46,204,113,0.08) !important; border-left: 3px solid var(--green-accent) !important; }
    .stWarning { background: rgba(240,192,64,0.08) !important; border-left: 3px solid var(--gold) !important; }
    .stSuccess { background: rgba(46,204,113,0.12) !important; border-left: 3px solid var(--green-accent) !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--green-deep); }
    ::-webkit-scrollbar-thumb { background: var(--green-mid); border-radius: 3px; }

    /* Spinner */
    .stSpinner > div { border-top-color: var(--green-accent) !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Navigation ───────────────────────────────────────────────────────────────
from ui import home, recommendation_page, monitoring_page, analytics_page, add_field_page

PAGES = {
    "🏠  Dashboard Home":       home,
    "🌱  Crop Recommendation":  recommendation_page,
    "🛰️  Satellite Monitoring": monitoring_page,
    "📊  Field Analytics":      analytics_page,
    "➕  Add New Field":         add_field_page,
}

# Sidebar logo / title
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center; padding: 8px 0 24px 0;'>
            <div style='font-size:2.8rem;'>🌾</div>
            <div style='font-family:Syne,sans-serif; font-size:1.25rem;
                        font-weight:800; color:#2ecc71; letter-spacing:1px;'>
                SmartAgri
            </div>
            <div style='font-size:0.7rem; color:#8ab89a; letter-spacing:2px;
                        text-transform:uppercase; margin-top:2px;'>
                Intelligence Platform
            </div>
        </div>
        <hr style='border-color:#1e3d28; margin-bottom:16px;'>
        """,
        unsafe_allow_html=True,
    )

    selection = st.radio(
        "Navigation",
        list(PAGES.keys()),
        label_visibility="collapsed",
    )

    st.markdown(
        """
        <hr style='border-color:#1e3d28; margin-top:24px;'>
        <div style='font-size:0.65rem; color:#4a7a5a; text-align:center;
                    padding-top:8px; font-family:DM Sans,sans-serif;'>
            SmartAgri v1.0 &nbsp;·&nbsp; Powered by GEE + ML
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Route to selected page ───────────────────────────────────────────────────
PAGES[selection].app()
