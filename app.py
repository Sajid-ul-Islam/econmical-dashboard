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

from utils.ui import inject_custom_css
inject_custom_css()

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
with st.sidebar:
    st.markdown("## 📊 EconVision")
    st.markdown("<p style='color:#64748B;font-size:11px;'>Global Economic Intelligence</p>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<p style='color:#374151;font-size:10px;text-align:center;margin-top:24px'>Sources: World Bank · FRED<br>ML: Prophet · Linear Trend<br>AI: Claude Sonnet</p>", unsafe_allow_html=True)

# ── Landing page ─────────────────────────────────────────────────────────────
st.switch_page("pages/Dashboard.py")
