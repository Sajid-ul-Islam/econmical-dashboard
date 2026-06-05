"""
Page 3 — AI Economic Agent
RAG-powered chat with Claude using live economic data as context
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="AI Agent — EconVision", page_icon="🤖", layout="wide")

from utils.ui import inject_custom_css
inject_custom_css()
from utils.ui import render_sidebar
render_sidebar()

from utils.agent import ask_agent, SUGGESTED_QUESTIONS
from utils.data_fetcher import get_country_data_cached, get_all_countries, load_country_data

# ── Load context ──────────────────────────────────────────────────────────
countries = st.session_state.get("selected_countries", ["USA", "CHN", "DEU"])
indicators = st.session_state.get("selected_indicators", ["gdp", "gdp_per_capita", "debt_pct_gdp"])
year_range = st.session_state.get("year_range", (2000, 2026))

all_countries_list = get_all_countries()
country_map = {c["code"]: c["name"] for c in all_countries_list}

df = st.session_state.get("current_df", pd.DataFrame())
if df.empty:
    with st.spinner("Loading data for AI context..."):
        for code in countries:
            load_country_data(code, country_map.get(code, code))
        df = get_country_data_cached(countries, indicators, year_range[0], min(year_range[1], 2026))
        st.session_state["current_df"] = df

predictions_df = st.session_state.get("predictions_df", pd.DataFrame())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ── Header ────────────────────────────────────────────────────────────────
col_h, col_btn = st.columns([4, 1])
with col_h:
    st.markdown("## 🤖 AI Economic Agent")
    cnames = [country_map.get(c, c) for c in countries[:4]]
    st.caption(f"Powered by Claude · Context: {', '.join(cnames)} · {len(df)} data points loaded")
with col_btn:
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

st.divider()

# ── Suggested questions ───────────────────────────────────────────────────
with st.expander("💡 Suggested Questions", expanded=len(st.session_state.chat_history) == 0):
    cols = st.columns(2)
    for i, q in enumerate(SUGGESTED_QUESTIONS):
        with cols[i % 2]:
            if st.button(q, key=f"sq_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": q})
                with st.spinner("Thinking..."):
                    response, model = ask_agent(
                        q, df, predictions_df, countries, indicators,
                        st.session_state.chat_history[:-1],
                    )
                st.session_state.chat_history.append({"role": "assistant", "content": response, "model": model})
                st.rerun()

# ── Chat history ──────────────────────────────────────────────────────────
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "📊"):
        st.markdown(msg["content"])
        if msg.get("model"):
            st.caption(f"⚡ Answered by: {msg['model']}")

# ── Input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about the economic data... (e.g. 'Which country has the highest debt?')"):
    st.session_state.chat_history.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="📊"):
        with st.spinner("Analysing economic data..."):
            response, model = ask_agent(
                prompt,
                df,
                predictions_df,
                countries,
                indicators,
                st.session_state.chat_history[:-1],
            )
        st.markdown(response)
        if model:
            st.caption(f"⚡ Answered by: {model}")

    st.session_state.chat_history.append({"role": "assistant", "content": response, "model": model})
    st.rerun()

# ── Context info panel ────────────────────────────────────────────────────
st.divider()
with st.expander("🔍 What data does the agent have access to?"):
    st.markdown("The agent receives this context on every query:")

    from utils.agent import build_data_context
    context = build_data_context(df, predictions_df, countries, indicators)
    st.code(context, language="text")
