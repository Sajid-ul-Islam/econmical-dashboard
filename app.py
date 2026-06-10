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
        "USA", "RUS", "GBR", "FRA", "CHN", 
        "IND", "PAK", "ISR", "PRK", "IRN"
    ],
    "selected_indicators": ["gdp", "gdp_per_capita", "debt_pct_gdp"],
    "year_range": (2000, 2026),
    "chat_history": [],
    "data_loaded": True,
    "custom_anthropic_key": "",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Navigation ──────────────────────────────────────────────────────────────
global_overview = st.Page("pages/Global_Overview.py", title="Global Overview", icon="🌍", default=True)
dashboard = st.Page("pages/Dashboard.py", title="Dashboard", icon="📈")
compare = st.Page("pages/Compare.py", title="Compare", icon="🔍")
data_lab = st.Page("pages/Data_Lab.py", title="Data Lab", icon="🗄️")
world_map = st.Page("pages/World_Map.py", title="World Map", icon="🗺️")
macro_trends = st.Page("pages/Macro_Trends.py", title="Macro Trends", icon="📉")

pg = st.navigation([global_overview, dashboard, world_map, compare, data_lab, macro_trends])
pg.run()
