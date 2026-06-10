"""
Page 1 — Global Overview: Global Market Indicators (Gold, Silver, Inflation, Unemployment, Oil, DXY)
"""

import sys
import os
import streamlit as st
import pandas as pd

# Ensure the project root is in sys.path to prevent module resolution errors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.ui import render_sidebar
    render_sidebar("Global Overview")

    from utils.data_fetcher import get_country_data_cached, get_all_countries, get_last_updated_str
    from utils.forecasting import get_or_create_forecasts_batch
    from components.charts import format_value, base_layout, add_event_annotations
    import plotly.graph_objects as go
except ImportError as e:
    st.error(f"🚨 **Import Error Detected:** `{e}`")
    st.warning("💡 **Fix:** This usually happens when a required library is missing from `requirements.txt`. Please check your dependencies (e.g., `requests`, `wbdata`, `fredapi`, `prophet`) and redeploy on Streamlit Cloud.")
    st.stop()

# ── Auto-load data ────────────────────────────────────────────────────────
all_countries = get_all_countries()
country_map = {c["code"]: c["name"] for c in all_countries}

countries = st.session_state.selected_countries
indicators = st.session_state.selected_indicators
year_range = st.session_state.year_range

with st.spinner("Loading global economic data..."):
    gold_df = get_country_data_cached(["WLD"], ["gold_price"], year_range[0], min(year_range[1], 2026))
    global_inflation_df = get_country_data_cached(["WLD"], ["inflation"], year_range[0], min(year_range[1], 2026))
    global_unemployment_df = get_country_data_cached(["WLD"], ["unemployment"], year_range[0], min(year_range[1], 2026))
    global_oil_df = get_country_data_cached(["WLD"], ["oil_price"], year_range[0], min(year_range[1], 2026))
    global_silver_df = get_country_data_cached(["WLD"], ["silver_price"], year_range[0], min(year_range[1], 2026))
    global_dxy_df = get_country_data_cached(["WLD"], ["dxy"], year_range[0], min(year_range[1], 2026))

# ── Fallback for Missing WLD Aggregates (Proxy by calculating Mean) ───────
if global_inflation_df.empty:
    if countries:
        proxy_infl_df = get_country_data_cached(countries, ["inflation"], year_range[0], min(year_range[1], 2026))
        if not proxy_infl_df.empty:
            global_inflation_df = proxy_infl_df.groupby("year", as_index=False)["value"].mean()
            global_inflation_df["country_code"] = "WLD"
            global_inflation_df["country_name"] = "World (Avg Proxy)"
            global_inflation_df["indicator"] = "inflation"

if global_unemployment_df.empty:
    if countries:
        proxy_unemp_df = get_country_data_cached(countries, ["unemployment"], year_range[0], min(year_range[1], 2026))
        if not proxy_unemp_df.empty:
            global_unemployment_df = proxy_unemp_df.groupby("year", as_index=False)["value"].mean()
            global_unemployment_df["country_code"] = "WLD"
            global_unemployment_df["country_name"] = "World (Avg Proxy)"
            global_unemployment_df["indicator"] = "unemployment"

# ── Build predictions ────────────────────────────────────────────────────
predictions_dfs = []
if st.session_state.show_predictions and year_range[1] > 2026:
    for g_df, g_ind in [
        (gold_df, "gold_price"), (global_inflation_df, "inflation"),
        (global_unemployment_df, "unemployment"), (global_oil_df, "oil_price"),
        (global_silver_df, "silver_price"), (global_dxy_df, "dxy")
    ]:
        if not g_df.empty:
            pred = get_or_create_forecasts_batch(g_df, ["WLD"], [g_ind])
            if not pred.empty:
                predictions_dfs.append(pred)

predictions_df = pd.concat(predictions_dfs, ignore_index=True) if predictions_dfs else pd.DataFrame()

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("## 🌍 Global Overview")
st.caption(f"Showing global market indices and macroeconomic averages · {year_range[0]}–{year_range[1]}")
st.divider()

@st.dialog("Expanded Chart View", width="large")
def open_expanded_chart(fig, df, pred_df, indicator):
    """A modal to show a larger chart with a data table and year slider."""
    
    modal_yr_start, modal_yr_end = st.slider(
        "Select Year Range to Display",
        min_value=int(df['year'].min()),
        max_value=int(df['year'].max()) if pred_df.empty else int(pred_df['year'].max()),
        value=(int(df['year'].min()), int(df['year'].max()) if pred_df.empty else int(pred_df['year'].max())),
        key=f"modal_slider_{indicator}"
    )

    # Filter figure data based on slider
    fig_large = go.Figure(fig).update_xaxes(range=[modal_yr_start, modal_yr_end])
    fig_large.update_layout(height=550)
    st.plotly_chart(fig_large, use_container_width=True)

    # Display data table
    hist_table = df[(df['indicator'] == indicator) & (df['year'] >= modal_yr_start) & (df['year'] <= modal_yr_end)]
    
    if not pred_df.empty:
        pred_table = pred_df[(pred_df['indicator'] == indicator) & (pred_df['year'] >= modal_yr_start) & (pred_df['year'] <= modal_yr_end)]
        
        # Combine for display
        hist_display = hist_table[['country_name', 'year', 'value']].rename(columns={'value': 'Historical Value'})
        pred_display = pred_table[['country_code', 'year', 'predicted']].rename(columns={'predicted': 'Forecasted Value'})
        
        # Need to map country name to predictions
        pred_display['country_name'] = pred_display['country_code'].map(country_map)
        
        full_table = pd.merge(hist_display, pred_display, on=['country_name', 'year'], how='outer').sort_values('year', ascending=False)
        st.dataframe(full_table, use_container_width=True, hide_index=True)
    else:
        st.dataframe(
            hist_table[['country_name', 'year', 'value']]
            .rename(columns={'value': 'Historical Value'})
            .sort_values('year', ascending=False),
            use_container_width=True,
            hide_index=True
        )

# ── Global Market Indicators ──────────────────────────────────────────────
if not gold_df.empty or not global_inflation_df.empty or not global_unemployment_df.empty or not global_oil_df.empty or not global_dxy_df.empty or not global_silver_df.empty:
    global_chart_cols = st.columns(2)
    g_col_idx = 0
    
    global_configs = [
        {"ind": "gold_price", "df": gold_df, "title": "#### 🟡 Global Gold Price", "color": "#FFD700", "fill": "rgba(255, 215, 0, 0.15)", "lyt": "Gold Price (USD/oz)", "y_title": "USD / oz", "hover": "<b>Gold Price</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>", "fcst_hover": "<b>Forecast</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>", "btn": "Gold Price"},
        {"ind": "silver_price", "df": global_silver_df, "title": "#### 🥈 Global Silver Price", "color": "#C0C0C0", "fill": "rgba(192, 192, 192, 0.15)", "lyt": "Silver Price (USD/oz)", "y_title": "USD / oz", "hover": "<b>Silver Price</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>", "fcst_hover": "<b>Forecast</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>", "btn": "Silver Price"},
        {"ind": "inflation", "df": global_inflation_df, "title": "#### 🎈 Global Inflation Rate", "color": "#FF6B6B", "fill": "rgba(255, 107, 107, 0.15)", "lyt": "Inflation Rate (%)", "y_title": "Annual %", "hover": "<b>Global Inflation</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>", "fcst_hover": "<b>Forecast</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>", "btn": "Inflation Rate"},
        {"ind": "unemployment", "df": global_unemployment_df, "title": "#### 👥 Global Unemployment", "color": "#00D4FF", "fill": "rgba(0, 212, 255, 0.15)", "lyt": "Unemployment Rate (%)", "y_title": "Total Labor Force (%)", "hover": "<b>Global Unemployment</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>", "fcst_hover": "<b>Forecast</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>", "btn": "Unemployment"},
        {"ind": "oil_price", "df": global_oil_df, "title": "#### 🛢️ Global Oil Price", "color": "#FF8B94", "fill": "rgba(255, 139, 148, 0.15)", "lyt": "Oil Price (Brent, USD/bbl)", "y_title": "USD / bbl", "hover": "<b>Oil Price</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>", "fcst_hover": "<b>Forecast</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>", "btn": "Oil Price"},
        {"ind": "dxy", "df": global_dxy_df, "title": "#### 💵 US Dollar (DXY)", "color": "#A8E6CF", "fill": "rgba(168, 230, 207, 0.15)", "lyt": "US Dollar Index", "y_title": "Index Value", "hover": "<b>DXY Index</b><br>Year: %{x}<br>Index: %{customdata}<br><br><i>Measures USD value vs a<br>basket of foreign currencies.</i><extra></extra>", "fcst_hover": "<b>Forecast</b><br>Year: %{x}<br>Index: %{customdata}<extra></extra>", "btn": "US Dollar (DXY)"}
    ]
    
    for config in global_configs:
        hist_df = config["df"]
        if hist_df.empty:
            continue
            
        with global_chart_cols[g_col_idx % 2]:
            st.markdown(config["title"])
            st.caption(f"Last updated: {get_last_updated_str(hist_df)}")
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist_df["year"], y=hist_df["value"],
                name="Historical",
                line=dict(color=config["color"], width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate=config["hover"],
                customdata=[format_value(v, config["ind"]) for v in hist_df["value"]]
            ))
        
            if st.session_state.show_predictions and year_range[1] > 2026 and not predictions_df.empty:
                pred_sub_df = predictions_df[predictions_df["indicator"] == config["ind"]]
                if not pred_sub_df.empty:
                    p_df = pred_sub_df[pred_sub_df["year"] <= year_range[1]]
                    
                    fig.add_trace(go.Scatter(
                        x=pd.concat([p_df["year"], p_df["year"][::-1]]),
                        y=pd.concat([p_df["upper_bound"], p_df["lower_bound"][::-1]]),
                        fill="toself",
                        fillcolor=config["fill"],
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig.add_trace(go.Scatter(
                        x=p_df["year"], y=p_df["predicted"],
                        name="Forecast",
                        line=dict(color=config["color"], width=2.5, dash="dash"),
                        hovertemplate=config["fcst_hover"],
                        customdata=[format_value(v, config["ind"]) for v in p_df["predicted"]]
                    ))
            
            layout = base_layout(config["lyt"], height=350)
            layout.setdefault("xaxis", {})["title"] = "Year"
            layout.setdefault("yaxis", {})["title"] = config["y_title"]
            fig.update_layout(**layout)
            add_event_annotations(fig, year_range)

            st.plotly_chart(fig, use_container_width=True)
            if st.button(f"🔍 Expand {config['btn']}", key=f"expand_btn_{config['ind']}_global", use_container_width=True):
                open_expanded_chart(fig, hist_df, predictions_df[predictions_df['indicator'] == config["ind"]] if not predictions_df.empty else pd.DataFrame(), config["ind"])
        
        g_col_idx += 1
else:
    st.info("No global economic indicators available in the current snapshot.")
