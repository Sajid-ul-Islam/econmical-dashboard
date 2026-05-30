"""
Global Economic Intelligence Dashboard
Main entry point — Streamlit multipage app
"""

import streamlit as st

st.set_page_config(
    page_title="EconVision — Global Economic Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 {
    font-family: 'Space Mono', monospace;
    letter-spacing: -0.5px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #0D1224 !important;
    border-right: 1px solid #1E2740;
}
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] p {
    color: #94A3B8 !important;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* KPI metric cards */
[data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1E2740;
    border-radius: 8px;
    padding: 16px;
}
[data-testid="metric-container"] label {
    color: #64748B !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #00D4FF !important;
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 12px !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00D4FF22, #00D4FF11);
    border: 1px solid #00D4FF44;
    color: #00D4FF;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    border-radius: 6px;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #00D4FF44, #00D4FF22);
    border-color: #00D4FF;
    box-shadow: 0 0 12px #00D4FF33;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    background: #111827;
    border: 1px solid #1E2740;
    border-radius: 6px;
    color: #64748B;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    padding: 8px 16px;
}
.stTabs [aria-selected="true"] {
    background: #00D4FF22 !important;
    border-color: #00D4FF44 !important;
    color: #00D4FF !important;
}

/* Chat messages */
.stChatMessage {
    background: #111827;
    border: 1px solid #1E2740;
    border-radius: 8px;
}

/* Expander */
.streamlit-expanderHeader {
    background: #111827;
    border: 1px solid #1E2740;
    border-radius: 6px;
    color: #94A3B8 !important;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
}

/* Divider */
hr { border-color: #1E2740; }

/* Status badges */
.badge-ok { color: #4ECDC4; font-size: 11px; }
.badge-stale { color: #FFE66D; font-size: 11px; }
.badge-error { color: #FF6B6B; font-size: 11px; }

/* Page header */
.page-header {
    border-bottom: 1px solid #1E2740;
    padding-bottom: 12px;
    margin-bottom: 24px;
}
.page-subtitle {
    color: #64748B;
    font-size: 13px;
    margin-top: -8px;
}
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ──────────────────────────────────────────────────
defaults = {
    "selected_countries": ["USA", "CHN", "DEU", "BGD"],
    "selected_indicators": ["gdp", "gdp_per_capita", "debt_pct_gdp"],
    "year_range": (2000, 2024),
    "chat_history": [],
    "data_loaded": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ─────────────────────────────────────────────────────────────────
from utils.data_fetcher import get_all_countries

with st.sidebar:
    st.markdown("## 📊 EconVision")
    st.markdown("<p style='color:#64748B;font-size:11px;'>Global Economic Intelligence</p>", unsafe_allow_html=True)
    st.divider()

    # Country selector
    all_countries = get_all_countries()
    country_options = {c["name"]: c["code"] for c in all_countries}
    country_names = list(country_options.keys())

    default_names = [
        name for name, code in country_options.items()
        if code in st.session_state.selected_countries
    ]

    selected_names = st.multiselect(
        "Countries",
        options=country_names,
        default=default_names[:6],
        max_selections=8,
        help="Select up to 8 countries",
    )
    st.session_state.selected_countries = [country_options[n] for n in selected_names]

    st.divider()

    # Indicator selector
    indicator_options = {
        "GDP (Total)": "gdp",
        "GDP Per Capita": "gdp_per_capita",
        "Debt % of GDP": "debt_pct_gdp",
        "Gold Price (Global)": "gold_price",
    }
    selected_ind_labels = st.multiselect(
        "Indicators",
        options=list(indicator_options.keys()),
        default=["GDP (Total)", "GDP Per Capita", "Debt % of GDP"],
    )
    st.session_state.selected_indicators = [indicator_options[l] for l in selected_ind_labels]

    st.divider()

    # Year range
    year_range = st.slider(
        "Year Range",
        min_value=1990,
        max_value=2031,
        value=st.session_state.year_range,
        step=1,
    )
    st.session_state.year_range = year_range

    st.divider()

    # Data refresh
    if st.button("🔄 Refresh Data", use_container_width=True):
        from utils.data_fetcher import load_country_data
        codes = st.session_state.selected_countries
        cmap = {c["code"]: c["name"] for c in all_countries}
        with st.spinner("Fetching from World Bank & FRED..."):
            for code in codes:
                name = cmap.get(code, code)
                load_country_data(code, name, force=True)
        st.cache_data.clear()
        st.success("Data refreshed!")
        st.rerun()

    st.markdown("<p style='color:#374151;font-size:10px;text-align:center;margin-top:24px'>Sources: World Bank · FRED<br>ML: Prophet · Linear Trend<br>AI: Claude Sonnet</p>", unsafe_allow_html=True)

# ── Landing page ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="page-header">
    <h1 style="font-size:2rem;margin:0">📊 EconVision</h1>
    <p class="page-subtitle">Global Economic Intelligence Dashboard — GDP · Debt · Gold · AI Analysis</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info("**📈 Dashboard**\nVisualise GDP, debt, and gold timelines with ML forecasts")
with col2:
    st.info("**🔍 Compare**\nSide-by-side country comparisons and correlation analysis")
with col3:
    st.info("**🤖 AI Agent**\nAsk economic questions — Claude answers using live data")
with col4:
    st.info("**🗄️ Data Lab**\nExplore data provenance, anomalies, and health scores")

st.markdown("---")
st.markdown("**👈 Use the sidebar to select countries and indicators, then navigate using the pages above.**")
st.caption("Navigate: use the sidebar pages or click the links above. Data auto-refreshes every 24 hours.")
