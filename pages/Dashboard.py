"""
Page 1 — Dashboard: KPI cards, timeline charts, and forecasts
"""

import sys
import os
import streamlit as st
import pandas as pd

# Ensure the project root is in sys.path to prevent module resolution errors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

st.set_page_config(page_title="Dashboard — EconVision", page_icon="📈", layout="wide")

try:
    from utils.ui import render_sidebar
    render_sidebar()

    from utils.data_fetcher import get_country_data_cached, get_all_countries, load_country_data, get_last_updated_str
    from utils.forecasting import get_or_create_forecast, detect_anomalies, compute_economic_health_score
    from components.charts import timeline_chart, health_score_gauge, format_value, base_layout, add_event_annotations, indicator_label
    import plotly.graph_objects as go
    from datetime import datetime
except ImportError as e:
    st.error(f"🚨 **Import Error Detected:** `{e}`")
    st.warning("💡 **Fix:** This usually happens when a required library is missing from `requirements.txt`. Please check your dependencies (e.g., `requests`, `wbdata`, `fredapi`, `prophet`) and redeploy on Streamlit Cloud.")
    st.stop()

countries = st.session_state.selected_countries
indicators = st.session_state.selected_indicators
year_range = st.session_state.year_range

if not countries:
    st.warning("👈 Select at least one country in the sidebar.")
    st.stop()

if not indicators:
    st.warning("👈 Select at least one indicator in the sidebar.")
    st.stop()

# ── Auto-load data ────────────────────────────────────────────────────────
all_countries = get_all_countries()
country_map = {c["code"]: c["name"] for c in all_countries}

with st.spinner("Loading economic data..."):
    for code in countries:
        name = country_map.get(code, code)
        load_country_data(code, name)  # no-op if fresh
        
    load_country_data("WLD", "World")

    df = get_country_data_cached(countries, indicators, year_range[0], min(year_range[1], 2026))
    gold_df = get_country_data_cached(["WLD"], ["gold_price"], year_range[0], min(year_range[1], 2026))
    global_inflation_df = get_country_data_cached(["WLD"], ["inflation"], year_range[0], min(year_range[1], 2026))
    global_unemployment_df = get_country_data_cached(["WLD"], ["unemployment"], year_range[0], min(year_range[1], 2026))
    global_oil_df = get_country_data_cached(["WLD"], ["oil_price"], year_range[0], min(year_range[1], 2026))
    global_silver_df = get_country_data_cached(["WLD"], ["silver_price"], year_range[0], min(year_range[1], 2026))
    global_dxy_df = get_country_data_cached(["WLD"], ["dxy"], year_range[0], min(year_range[1], 2026))

if df.empty:
    st.error("No data found. Try clicking **Refresh Data** in the sidebar.")
    st.stop()

# ── Fallback for Missing WLD Aggregates (Proxy by calculating Mean) ───────
if global_inflation_df.empty and not df[df["indicator"] == "inflation"].empty:
    global_inflation_df = df[df["indicator"] == "inflation"].groupby("year", as_index=False)["value"].mean()
    global_inflation_df["country_code"] = "WLD"
    global_inflation_df["country_name"] = "World (Avg Proxy)"
    global_inflation_df["indicator"] = "inflation"

if global_unemployment_df.empty and not df[df["indicator"] == "unemployment"].empty:
    global_unemployment_df = df[df["indicator"] == "unemployment"].groupby("year", as_index=False)["value"].mean()
    global_unemployment_df["country_code"] = "WLD"
    global_unemployment_df["country_name"] = "World (Avg Proxy)"
    global_unemployment_df["indicator"] = "unemployment"

# ── Apply sorting based on latest values ─────────────────────────────────
kpi_indicator = indicators[0]
latest_year = int(df["year"].max())
latest_df = df[(df["indicator"] == kpi_indicator) & (df["year"] == latest_year)]
if not latest_df.empty:
    ascending = st.session_state.sort_order == "Lowest to Highest"
    sorted_codes = latest_df.sort_values("value", ascending=ascending)["country_code"].tolist()
    countries = [c for c in sorted_codes if c in countries] + [c for c in countries if c not in sorted_codes]
    df["country_code"] = pd.Categorical(df["country_code"], categories=countries, ordered=True)
    df = df.sort_values(["country_code", "year"])

# ── Build predictions ────────────────────────────────────────────────────
predictions_dfs = []
if st.session_state.show_predictions and year_range[1] > 2026:
    for code in countries:
        for indicator in indicators:
            cdf = df[(df["country_code"] == code) & (df["indicator"] == indicator)]
            if not cdf.empty:
                pred = get_or_create_forecast(cdf, code, indicator)
                if not pred.empty:
                    predictions_dfs.append(pred)

    if not gold_df.empty:
        gold_pred = get_or_create_forecast(gold_df, "WLD", "gold_price")
        if not gold_pred.empty:
            predictions_dfs.append(gold_pred)

    if not global_inflation_df.empty:
        inflation_pred = get_or_create_forecast(global_inflation_df, "WLD", "inflation")
        if not inflation_pred.empty:
            predictions_dfs.append(inflation_pred)

    if not global_unemployment_df.empty:
        unemp_pred = get_or_create_forecast(global_unemployment_df, "WLD", "unemployment")
        if not unemp_pred.empty:
            predictions_dfs.append(unemp_pred)

    if not global_oil_df.empty:
        oil_pred = get_or_create_forecast(global_oil_df, "WLD", "oil_price")
        if not oil_pred.empty:
            predictions_dfs.append(oil_pred)

    if not global_silver_df.empty:
        silver_pred = get_or_create_forecast(global_silver_df, "WLD", "silver_price")
        if not silver_pred.empty:
            predictions_dfs.append(silver_pred)

    if not global_dxy_df.empty:
        dxy_pred = get_or_create_forecast(global_dxy_df, "WLD", "dxy")
        if not dxy_pred.empty:
            predictions_dfs.append(dxy_pred)

predictions_df = pd.concat(predictions_dfs, ignore_index=True) if predictions_dfs else pd.DataFrame()
st.session_state["current_df"] = df
st.session_state["predictions_df"] = predictions_df

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("## 📈 Dashboard")
st.caption(f"Showing {len(countries)} countries · {len(indicators)} indicators · {year_range[0]}–{year_range[1]}")
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

# ── Global Market Indicators (Top) ────────────────────────────────────────
if not gold_df.empty or not global_inflation_df.empty or not global_unemployment_df.empty or not global_oil_df.empty or not global_dxy_df.empty or not global_silver_df.empty:
    global_chart_cols = st.columns(2)
    g_col_idx = 0
    
    if not gold_df.empty:
        with global_chart_cols[g_col_idx % 2]:
            st.markdown("#### 🟡 Global Gold Price")
            st.caption(f"Last updated: {get_last_updated_str(gold_df)}")
            fig_gold = go.Figure()
            
            fig_gold.add_trace(go.Scatter(
                x=gold_df["year"], y=gold_df["value"],
                name="Historical",
                line=dict(color="#FFD700", width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate="<b>Gold Price</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>",
                customdata=[format_value(v, "gold_price") for v in gold_df["value"]]
            ))
        
            if st.session_state.show_predictions and year_range[1] > 2026:
                if 'gold_pred' in locals() and not gold_pred.empty:
                    gp = gold_pred[gold_pred["year"] <= year_range[1]]
                    
                    fig_gold.add_trace(go.Scatter(
                        x=pd.concat([gp["year"], gp["year"][::-1]]),
                        y=pd.concat([gp["upper_bound"], gp["lower_bound"][::-1]]),
                        fill="toself",
                        fillcolor="rgba(255, 215, 0, 0.15)",
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig_gold.add_trace(go.Scatter(
                        x=gp["year"], y=gp["predicted"],
                        name="Forecast",
                        line=dict(color="#FFD700", width=2.5, dash="dash"),
                        hovertemplate="<b>Forecast</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>",
                        customdata=[format_value(v, "gold_price") for v in gp["predicted"]]
                    ))
            
            layout = base_layout("Gold Price (USD/oz)", height=350)
            layout["xaxis"]["title"] = "Year"
            layout["yaxis"]["title"] = "USD / oz"
            fig_gold.update_layout(**layout)
            add_event_annotations(fig_gold, year_range)

            st.plotly_chart(fig_gold, use_container_width=True)
            if st.button("🔍 Expand Gold Price", key="expand_btn_gold_global", use_container_width=True):
                open_expanded_chart(fig_gold, gold_df, predictions_df[predictions_df['indicator'] == 'gold_price'], 'gold_price')
        g_col_idx += 1

    if not global_silver_df.empty:
        with global_chart_cols[g_col_idx % 2]:
            st.markdown("#### 🥈 Global Silver Price")
            st.caption(f"Last updated: {get_last_updated_str(global_silver_df)}")
            fig_silver = go.Figure()
            
            fig_silver.add_trace(go.Scatter(
                x=global_silver_df["year"], y=global_silver_df["value"],
                name="Historical",
                line=dict(color="#C0C0C0", width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate="<b>Silver Price</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>",
                customdata=[format_value(v, "silver_price") for v in global_silver_df["value"]]
            ))

            if st.session_state.show_predictions and year_range[1] > 2026:
                if 'silver_pred' in locals() and not silver_pred.empty:
                    sp = silver_pred[silver_pred["year"] <= year_range[1]]
                    
                    fig_silver.add_trace(go.Scatter(
                        x=pd.concat([sp["year"], sp["year"][::-1]]),
                        y=pd.concat([sp["upper_bound"], sp["lower_bound"][::-1]]),
                        fill="toself",
                        fillcolor="rgba(192, 192, 192, 0.15)",
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig_silver.add_trace(go.Scatter(
                        x=sp["year"], y=sp["predicted"],
                        name="Forecast",
                        line=dict(color="#C0C0C0", width=2.5, dash="dash"),
                        hovertemplate="<b>Forecast</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>",
                        customdata=[format_value(v, "silver_price") for v in sp["predicted"]]
                    ))
            
            layout_silver = base_layout("Silver Price (USD/oz)", height=350)
            layout_silver["xaxis"]["title"] = "Year"
            layout_silver["yaxis"]["title"] = "USD / oz"
            fig_silver.update_layout(**layout_silver)
            add_event_annotations(fig_silver, year_range)

            st.plotly_chart(fig_silver, use_container_width=True)
            if st.button("🔍 Expand Silver Price", key="expand_btn_silver_global", use_container_width=True):
                open_expanded_chart(fig_silver, global_silver_df, predictions_df[predictions_df['indicator'] == 'silver_price'], 'silver_price')
        g_col_idx += 1

    if not global_inflation_df.empty:
        with global_chart_cols[g_col_idx % 2]:
            st.markdown("#### 🎈 Global Inflation Rate")
            st.caption(f"Last updated: {get_last_updated_str(global_inflation_df)}")
            fig_infl = go.Figure()
            
            fig_infl.add_trace(go.Scatter(
                x=global_inflation_df["year"], y=global_inflation_df["value"],
                name="Historical",
                line=dict(color="#FF6B6B", width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate="<b>Global Inflation</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>",
                customdata=[format_value(v, "inflation") for v in global_inflation_df["value"]]
            ))

            if st.session_state.show_predictions and year_range[1] > 2026:
                if 'inflation_pred' in locals() and not inflation_pred.empty:
                    ip = inflation_pred[inflation_pred["year"] <= year_range[1]]
                    
                    fig_infl.add_trace(go.Scatter(
                        x=pd.concat([ip["year"], ip["year"][::-1]]),
                        y=pd.concat([ip["upper_bound"], ip["lower_bound"][::-1]]),
                        fill="toself",
                        fillcolor="rgba(255, 107, 107, 0.15)",
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig_infl.add_trace(go.Scatter(
                        x=ip["year"], y=ip["predicted"],
                        name="Forecast",
                        line=dict(color="#FF6B6B", width=2.5, dash="dash"),
                        hovertemplate="<b>Forecast</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>",
                        customdata=[format_value(v, "inflation") for v in ip["predicted"]]
                    ))
            
            layout_infl = base_layout("Inflation Rate (%)", height=350)
            layout_infl["xaxis"]["title"] = "Year"
            layout_infl["yaxis"]["title"] = "Annual %"
            fig_infl.update_layout(**layout_infl)
            add_event_annotations(fig_infl, year_range)

            st.plotly_chart(fig_infl, use_container_width=True)
            if st.button("🔍 Expand Inflation Rate", key="expand_btn_infl_global", use_container_width=True):
                open_expanded_chart(fig_infl, global_inflation_df, predictions_df[predictions_df['indicator'] == 'inflation'], 'inflation')
        g_col_idx += 1

    if not global_unemployment_df.empty:
        with global_chart_cols[g_col_idx % 2]:
            st.markdown("#### 👥 Global Unemployment")
            st.caption(f"Last updated: {get_last_updated_str(global_unemployment_df)}")
            fig_unemp = go.Figure()
            
            fig_unemp.add_trace(go.Scatter(
                x=global_unemployment_df["year"], y=global_unemployment_df["value"],
                name="Historical",
                line=dict(color="#00D4FF", width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate="<b>Global Unemployment</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>",
                customdata=[format_value(v, "unemployment") for v in global_unemployment_df["value"]]
            ))

            if st.session_state.show_predictions and year_range[1] > 2026:
                if 'unemp_pred' in locals() and not unemp_pred.empty:
                    up = unemp_pred[unemp_pred["year"] <= year_range[1]]
                    
                    fig_unemp.add_trace(go.Scatter(
                        x=pd.concat([up["year"], up["year"][::-1]]),
                        y=pd.concat([up["upper_bound"], up["lower_bound"][::-1]]),
                        fill="toself",
                        fillcolor="rgba(0, 212, 255, 0.15)",
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig_unemp.add_trace(go.Scatter(
                        x=up["year"], y=up["predicted"],
                        name="Forecast",
                        line=dict(color="#00D4FF", width=2.5, dash="dash"),
                        hovertemplate="<b>Forecast</b><br>Year: %{x}<br>Rate: %{customdata}<extra></extra>",
                        customdata=[format_value(v, "unemployment") for v in up["predicted"]]
                    ))
            
            layout_unemp = base_layout("Unemployment Rate (%)", height=350)
            layout_unemp["xaxis"]["title"] = "Year"
            layout_unemp["yaxis"]["title"] = "Total Labor Force (%)"
            fig_unemp.update_layout(**layout_unemp)
            add_event_annotations(fig_unemp, year_range)

            st.plotly_chart(fig_unemp, use_container_width=True)
            if st.button("🔍 Expand Unemployment", key="expand_btn_unemp_global", use_container_width=True):
                open_expanded_chart(fig_unemp, global_unemployment_df, predictions_df[predictions_df['indicator'] == 'unemployment'], 'unemployment')
        g_col_idx += 1

    if not global_oil_df.empty:
        with global_chart_cols[g_col_idx % 2]:
            st.markdown("#### 🛢️ Global Oil Price")
            st.caption(f"Last updated: {get_last_updated_str(global_oil_df)}")
            fig_oil = go.Figure()
            
            fig_oil.add_trace(go.Scatter(
                x=global_oil_df["year"], y=global_oil_df["value"],
                name="Historical",
                line=dict(color="#FF8B94", width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate="<b>Oil Price</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>",
                customdata=[format_value(v, "oil_price") for v in global_oil_df["value"]]
            ))

            if st.session_state.show_predictions and year_range[1] > 2026:
                if 'oil_pred' in locals() and not oil_pred.empty:
                    op = oil_pred[oil_pred["year"] <= year_range[1]]
                    
                    fig_oil.add_trace(go.Scatter(
                        x=pd.concat([op["year"], op["year"][::-1]]),
                        y=pd.concat([op["upper_bound"], op["lower_bound"][::-1]]),
                        fill="toself",
                        fillcolor="rgba(255, 139, 148, 0.15)",
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig_oil.add_trace(go.Scatter(
                        x=op["year"], y=op["predicted"],
                        name="Forecast",
                        line=dict(color="#FF8B94", width=2.5, dash="dash"),
                        hovertemplate="<b>Forecast</b><br>Year: %{x}<br>Price: %{customdata}<extra></extra>",
                        customdata=[format_value(v, "oil_price") for v in op["predicted"]]
                    ))
            
            layout_oil = base_layout("Oil Price (Brent, USD/bbl)", height=350)
            layout_oil["xaxis"]["title"] = "Year"
            layout_oil["yaxis"]["title"] = "USD / bbl"
            fig_oil.update_layout(**layout_oil)
            add_event_annotations(fig_oil, year_range)

            st.plotly_chart(fig_oil, use_container_width=True)
            if st.button("🔍 Expand Oil Price", key="expand_btn_oil_global", use_container_width=True):
                open_expanded_chart(fig_oil, global_oil_df, predictions_df[predictions_df['indicator'] == 'oil_price'], 'oil_price')
        g_col_idx += 1

    if not global_dxy_df.empty:
        with global_chart_cols[g_col_idx % 2]:
            st.markdown("#### 💵 US Dollar (DXY)")
            st.caption(f"Last updated: {get_last_updated_str(global_dxy_df)}")
            fig_dxy = go.Figure()
            
            fig_dxy.add_trace(go.Scatter(
                x=global_dxy_df["year"], y=global_dxy_df["value"],
                name="Historical",
                line=dict(color="#A8E6CF", width=2.5),
                mode="lines+markers",
                marker=dict(size=5),
                hovertemplate="<b>DXY Index</b><br>Year: %{x}<br>Index: %{customdata}<br><br><i>Measures USD value vs a<br>basket of foreign currencies.</i><extra></extra>",
                customdata=[format_value(v, "dxy") for v in global_dxy_df["value"]]
            ))

            if st.session_state.show_predictions and year_range[1] > 2026:
                if 'dxy_pred' in locals() and not dxy_pred.empty:
                    dp = dxy_pred[dxy_pred["year"] <= year_range[1]]
                    
                    fig_dxy.add_trace(go.Scatter(
                        x=pd.concat([dp["year"], dp["year"][::-1]]),
                        y=pd.concat([dp["upper_bound"], dp["lower_bound"][::-1]]),
                        fill="toself",
                        fillcolor="rgba(168, 230, 207, 0.15)",
                        line=dict(color="rgba(0,0,0,0)"),
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig_dxy.add_trace(go.Scatter(
                        x=dp["year"], y=dp["predicted"],
                        name="Forecast",
                        line=dict(color="#A8E6CF", width=2.5, dash="dash"),
                        hovertemplate="<b>Forecast</b><br>Year: %{x}<br>Index: %{customdata}<extra></extra>",
                        customdata=[format_value(v, "dxy") for v in dp["predicted"]]
                    ))
            
            layout_dxy = base_layout("US Dollar Index", height=350)
            layout_dxy["xaxis"]["title"] = "Year"
            layout_dxy["yaxis"]["title"] = "Index Value"
            fig_dxy.update_layout(**layout_dxy)
            add_event_annotations(fig_dxy, year_range)

            st.plotly_chart(fig_dxy, use_container_width=True)
            if st.button("🔍 Expand US Dollar (DXY)", key="expand_btn_dxy_global", use_container_width=True):
                open_expanded_chart(fig_dxy, global_dxy_df, predictions_df[predictions_df['indicator'] == 'dxy'], 'dxy')
        g_col_idx += 1

    st.divider()

# ── KPI Cards ─────────────────────────────────────────────────────────────
st.markdown("#### Latest Values")
latest_year = int(df["year"].max())
kpi_indicator = indicators[0]

latest_df = df[(df["indicator"] == kpi_indicator) & (df["year"] == latest_year)]

if not latest_df.empty:
    cols = st.columns(min(len(countries), 5))
    for i, code in enumerate(countries[:5]):
        row = latest_df[latest_df["country_code"] == code]
        if row.empty:
            continue
        val = row["value"].iloc[0]
        cname = row["country_name"].iloc[0] if "country_name" in row.columns else code

        # YoY delta
        prev = df[(df["country_code"] == code) & (df["indicator"] == kpi_indicator) & (df["year"] == latest_year - 1)]
        delta = None
        if not prev.empty:
            prev_val = prev["value"].iloc[0]
            if prev_val and prev_val != 0:
                delta = f"{((val - prev_val) / abs(prev_val)) * 100:+.1f}% YoY"

        with cols[i % 5]:
            st.metric(
                label=f"{cname[:18]} ({latest_year})",
                value=format_value(val, kpi_indicator),
                delta=delta,
            )

# ── Economic Health Scores ────────────────────────────────────────────────
st.divider()
st.markdown("#### 🏆 Economic Health Scores")
st.caption("Composite score based on GDP per capita and debt ratio (0 = weak, 100 = strong)")

score_cols = st.columns(min(len(countries), 5))
for i, code in enumerate(countries[:5]):
    cdf = df[df["country_code"] == code]
    if cdf.empty:
        continue
    cname = cdf["country_name"].iloc[0] if "country_name" in cdf.columns else code
    scores = compute_economic_health_score(cdf, latest_year)
    with score_cols[i % 5]:
        fig = health_score_gauge(scores.get("composite", 50), cname)
        st.plotly_chart(fig, use_container_width=True)

# ── Timeline Charts ───────────────────────────────────────────────────────
st.divider()
st.markdown("#### Time Series")

chart_cols = st.columns(2)
for i, indicator in enumerate(indicators):
    with chart_cols[i % 2]:
        ind_df = df[df["indicator"] == indicator]
        if ind_df.empty:
            continue
        pred_df = predictions_df[predictions_df["country_code"].isin(countries)] if not predictions_df.empty else pd.DataFrame()
        ind_df_plot = ind_df[ind_df["country_code"].isin(countries)]
        
        st.caption(f"Last updated: {get_last_updated_str(ind_df_plot)}")
        
        fig = timeline_chart(ind_df_plot, pred_df, indicator, year_range)
        
        st.plotly_chart(fig, use_container_width=True)
        
        if st.button(f"🔍 Expand {indicator_label(indicator)}", key=f"expand_btn_{indicator}", use_container_width=True):
            open_expanded_chart(fig, ind_df_plot, pred_df, indicator)

# ── Anomaly Flags ─────────────────────────────────────────────────────────
st.divider()
st.markdown("#### 🚨 Anomaly Detection")
st.caption("Flagging unusual year-over-year changes (z-score > 2.5)")

anomaly_found = False
for code in countries:
    for indicator in indicators:
        cdf = df[(df["country_code"] == code) & (df["indicator"] == indicator)].copy()
        if len(cdf) < 4:
            continue
        result = detect_anomalies(cdf)
        anomalies = result[result["anomaly"] == True]
        if not anomalies.empty:
            anomaly_found = True
            cname = cdf["country_name"].iloc[0] if "country_name" in cdf.columns else code
            for _, row in anomalies.iterrows():
                st.markdown(
                    f"⚠️ **{cname}** — `{indicator}` in **{int(row['year'])}**: "
                    f"{row['yoy_growth']:+.1f}% YoY change (z={row['z_score']:.1f})"
                )

if not anomaly_found:
    st.success("✅ No significant anomalies detected in the current selection.")
