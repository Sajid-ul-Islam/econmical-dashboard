"""
Page 1 — Dashboard: KPI cards, timeline charts, and forecasts
"""

import sys
import os
import streamlit as st
import pandas as pd

# Ensure the project root is in sys.path to prevent module resolution errors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from utils.ui import render_sidebar
    render_sidebar()

    from utils.data_fetcher import get_country_data_cached, get_all_countries, get_last_updated_str
    from utils.forecasting import get_or_create_forecasts_batch, detect_anomalies, compute_economic_health_score
    from components.charts import timeline_chart, health_score_gauge, format_value, base_layout, add_event_annotations, indicator_label
    import plotly.graph_objects as go
except ImportError as e:
    st.error(f"🚨 **Import Error Detected:** `{e}`")
    st.warning("💡 **Fix:** This usually happens when a required library is missing from `requirements.txt`. Please check your dependencies (e.g., `requests`, `wbdata`, `fredapi`, `prophet`) and redeploy on Streamlit Cloud.")
    st.stop()

countries = st.session_state.selected_countries
indicators = st.session_state.selected_indicators
year_range = st.session_state.year_range

# ── Auto-load data ────────────────────────────────────────────────────────
all_countries = get_all_countries()
country_map = {c["code"]: c["name"] for c in all_countries}

with st.spinner("Loading economic data..."):

    if countries and indicators:
        df = get_country_data_cached(countries, indicators, year_range[0], min(year_range[1], 2026))
    else:
        df = pd.DataFrame()

# ── Apply sorting based on latest values ─────────────────────────────────
if not df.empty and indicators:
    kpi_indicator = indicators[0]
    kpi_df = df[df["indicator"] == kpi_indicator]
    latest_df = kpi_df.sort_values("year").groupby("country_code", as_index=False).tail(1)
    if not latest_df.empty:
        ascending = st.session_state.sort_order == "Lowest to Highest"
        sorted_codes = latest_df.sort_values("value", ascending=ascending)["country_code"].tolist()
        countries = [c for c in sorted_codes if c in countries] + [c for c in countries if c not in sorted_codes]
        df["country_code"] = pd.Categorical(df["country_code"], categories=countries, ordered=True)
        df = df.sort_values(["country_code", "year"])

# ── Build predictions ────────────────────────────────────────────────────
predictions_dfs = []
if st.session_state.show_predictions and year_range[1] > 2026:
    # Batch fetch for all main countries
    if not df.empty and countries and indicators:
        main_preds = get_or_create_forecasts_batch(df, countries, indicators)
        if not main_preds.empty:
            predictions_dfs.append(main_preds)

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



# ── Verify Selections for Local Market Analysis ──────────────────────────
if not countries:
    st.info("👈 Select at least one country in the sidebar to view local market analysis.")
    st.stop()

if not indicators:
    st.info("👈 Select at least one indicator in the sidebar to view local market analysis.")
    st.stop()

if df.empty:
    st.error("No local market data found for current selection. Try clicking **Refresh Data** in the sidebar.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────────────
st.markdown("#### Latest Values")
kpi_indicator = indicators[0]

kpi_df = df[df["indicator"] == kpi_indicator]
latest_df = kpi_df.sort_values("year").groupby("country_code", as_index=False).tail(1)

if not latest_df.empty:
    global_max_year = int(kpi_df["year"].max()) if not kpi_df.empty else 2026
    cols_per_row = 6
    for r in range(0, len(countries), cols_per_row):
        chunk = countries[r:r+cols_per_row]
        cols = st.columns(cols_per_row)
        for i, code in enumerate(chunk):
            row = latest_df[latest_df["country_code"] == code]
            if row.empty:
                continue
            val = row["value"].iloc[0]
            c_year = int(row["year"].iloc[0])
            cname = row["country_name"].iloc[0] if "country_name" in row.columns else code

            # YoY delta
            prev = df[(df["country_code"] == code) & (df["indicator"] == kpi_indicator) & (df["year"] == c_year - 1)]
            delta = None
            if not prev.empty:
                prev_val = prev["value"].iloc[0]
                if prev_val and prev_val != 0:
                    delta = f"{((val - prev_val) / abs(prev_val)) * 100:+.1f}% YoY"

            year_display = f"{c_year}" if c_year >= global_max_year else f"{c_year} ⏳"

            with cols[i]:
                st.metric(
                    label=f"{cname[:18]} ({year_display})",
                    value=format_value(val, kpi_indicator),
                    delta=delta,
                )

# ── Economic Health Scores ────────────────────────────────────────────────
st.divider()
st.markdown("#### 🏆 Economic Health Scores")
st.caption("Composite score based on GDP per capita and debt ratio (0 = weak, 100 = strong)")

cols_per_row = 6
for r in range(0, len(countries), cols_per_row):
    chunk = countries[r:r+cols_per_row]
    score_cols = st.columns(cols_per_row)
    for i, code in enumerate(chunk):
        cdf = df[df["country_code"] == code]
        if cdf.empty:
            continue
        cname = cdf["country_name"].iloc[0] if "country_name" in cdf.columns else code
        c_latest_year = int(cdf["year"].max())
        scores = compute_economic_health_score(cdf, c_latest_year)
        with score_cols[i]:
            fig = health_score_gauge(scores.get("composite", 50), cname)
            st.plotly_chart(fig, use_container_width=True)

# ── Timeline Charts ───────────────────────────────────────────────────────
st.divider()
st.markdown("#### Time Series")

plot_indicators = list(indicators)
if "inflation" not in plot_indicators:
    plot_indicators.append("inflation")
    country_infl_df = get_country_data_cached(countries, ["inflation"], year_range[0], min(year_range[1], 2026))
    if not country_infl_df.empty:
        df = pd.concat([df, country_infl_df], ignore_index=True)
        if st.session_state.show_predictions and year_range[1] > 2026:
            country_infl_pred = get_or_create_forecasts_batch(country_infl_df, countries, ["inflation"])
            if not country_infl_pred.empty:
                if predictions_df.empty:
                    predictions_df = country_infl_pred
                else:
                    predictions_df = pd.concat([predictions_df, country_infl_pred], ignore_index=True)

if "unemployment" not in plot_indicators:
    plot_indicators.append("unemployment")
    country_unemp_df = get_country_data_cached(countries, ["unemployment"], year_range[0], min(year_range[1], 2026))
    if not country_unemp_df.empty:
        df = pd.concat([df, country_unemp_df], ignore_index=True)
        if st.session_state.show_predictions and year_range[1] > 2026:
            country_unemp_pred = get_or_create_forecasts_batch(country_unemp_df, countries, ["unemployment"])
            if not country_unemp_pred.empty:
                if predictions_df.empty:
                    predictions_df = country_unemp_pred
                else:
                    predictions_df = pd.concat([predictions_df, country_unemp_pred], ignore_index=True)

chart_cols = st.columns(2)
for i, indicator in enumerate(plot_indicators):
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
    for indicator in plot_indicators:
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
