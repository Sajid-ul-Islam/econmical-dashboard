"""
Global Economic Intelligence Dashboard
Main entry point — Streamlit multipage app
"""

import streamlit as st
import os

# ── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EconVision",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Hugging Face Spaces Secrets Handler ─────────────────────────────────────
# HF Spaces exposes secrets as environment variables. We map a single TOML 
# string secret to Streamlit's required secrets.toml file on boot.
if "SECRETS_TOML" in os.environ and not os.path.exists(".streamlit/secrets.toml"):
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w") as f:
        f.write(os.environ["SECRETS_TOML"])

# ── Session state defaults ──────────────────────────────────────────────────
defaults = {
    "selected_countries": [
        "USA", "CAN", "BLZ", "HTI",  # North America
        "BRA", "ARG", "SUR", "GUY",  # South America
        "DEU", "GBR", "MNE", "ISL",  # Europe
        "CHN", "JPN", "MDV", "BTN",  # Asia
        "NGA", "ZAF", "COM", "DJI",  # Africa
        "AUS", "NZL", "TUV", "NRU",  # Oceania
        "IDN", "SAU", "GMB", "SOM"   # Top & Bottom Muslim
    ],
    "selected_indicators": ["gdp", "gdp_per_capita", "debt_pct_gdp"],
    "year_range": (2000, 2026),
    "chat_history": [],
    "data_loaded": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Pre-warm Data Cache ─────────────────────────────────────────────────────
if not st.session_state.data_loaded:
    from utils.data_fetcher import get_country_data_cached
    get_country_data_cached(
        st.session_state.selected_countries, 
        st.session_state.selected_indicators, 
        st.session_state.year_range[0], 
        min(st.session_state.year_range[1], 2026)
    )
    st.session_state.data_loaded = True

# ── Navigation ──────────────────────────────────────────────────────────────
dashboard = st.Page("pages/Dashboard.py", title="Dashboard", icon="📈", default=True)
compare = st.Page("pages/Compare.py", title="Compare", icon="🔍")
data_lab = st.Page("pages/Data_Lab.py", title="Data Lab", icon="🗄️")
world_map = st.Page("pages/World_Map.py", title="World Map", icon="🌍")

pg = st.navigation([dashboard, world_map, compare, data_lab])
pg.run()
