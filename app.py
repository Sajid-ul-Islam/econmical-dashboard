"""
Global Economic Intelligence Dashboard
Main entry point — Streamlit multipage app
"""

import streamlit as st

# ── Session state defaults ──────────────────────────────────────────────────
defaults = {
    "selected_countries": ["USA", "CHN", "DEU", "BGD"],
    "selected_indicators": ["gdp", "gdp_per_capita", "debt_pct_gdp"],
    "year_range": (2000, 2026),
    "chat_history": [],
    "data_loaded": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Navigation ──────────────────────────────────────────────────────────────
dashboard = st.Page("pages/Dashboard.py", title="Dashboard", icon="📈", default=True)
compare = st.Page("pages/Compare.py", title="Compare", icon="🔍")
data_lab = st.Page("pages/Data_Lab.py", title="Data Lab", icon="🗄️")
world_map = st.Page("pages/World_Map.py", title="World Map", icon="🌍")

pg = st.navigation([dashboard, world_map, compare, data_lab])
pg.run()
