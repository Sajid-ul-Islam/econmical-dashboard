"""
Page 1 — Dashboard: KPI cards, timeline charts, and forecasts
"""

import streamlit as st
import pandas as pd

st.set_page_config(page_title="Dashboard — EconVision", page_icon="📈", layout="wide")

from utils.ui import inject_custom_css
inject_custom_css()

from utils.data_fetcher import get_country_data_cached, get_all_countries, load_country_data
from utils.forecasting import get_or_create_forecast, detect_anomalies, compute_economic_health_score
from components.charts import timeline_chart, health_score_gauge, format_value

# ── Load session state ────────────────────────────────────────────────────
all_countries = get_all_countries()
country_options = {c["name"]: c["code"] for c in all_countries}
country_names = list(country_options.keys())

indicator_options = {
    "GDP (Total)": "gdp",
    "GDP Per Capita": "gdp_per_capita",
    "Debt % of GDP": "debt_pct_gdp",
    "Gold Price (Global)": "gold_price",
}

with st.sidebar:
    st.markdown("### ⚙️ Dashboard Options")
    
    default_names = [name for name, code in country_options.items() if code in st.session_state.get("selected_countries", ["USA", "CHN", "DEU"])]
    selected_names = st.multiselect(
        "Countries",
        options=country_names,
        default=default_names[:6],
        max_selections=8,
    )
    st.session_state.selected_countries = [country_options[n] for n in selected_names]
    
    default_inds = [k for k, v in indicator_options.items() if v in st.session_state.get("selected_indicators", ["gdp", "gdp_per_capita", "debt_pct_gdp"])]
    selected_ind_labels = st.multiselect(
        "Indicators",
        options=list(indicator_options.keys()),
        default=default_inds,
    )
    st.session_state.selected_indicators = [indicator_options[l] for l in selected_ind_labels]
    
    st.session_state.year_range = st.slider(
        "Year Range",
        min_value=1990,
        max_value=2031,
        value=st.session_state.get("year_range", (2000, 2024)),
        step=1,
    )

    st.session_state.sort_order = st.selectbox(
        "Sort Order (Primary Indicator)",
        options=["Highest to Lowest", "Lowest to Highest"],
        index=0 if st.session_state.get("sort_order", "Highest to Lowest") == "Highest to Lowest" else 1,
    )

    st.session_state.show_predictions = st.toggle(
        "Show ML Predictions",
        value=st.session_state.get("show_predictions", True),
    )

    if st.button("🔄 Refresh Data", use_container_width=True):
        with st.spinner("Fetching from World Bank & FRED..."):
            for code in st.session_state.selected_countries:
                load_country_data(code, {v: k for k, v in country_options.items()}.get(code, code), force=True)
        st.cache_data.clear()
        st.success("Data refreshed!")
        st.rerun()

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
country_map = {c["code"]: c["name"] for c in all_countries}

with st.spinner("Loading economic data..."):
    for code in countries:
        name = country_map.get(code, code)
        load_country_data(code, name)  # no-op if fresh

    df = get_country_data_cached(countries, indicators, year_range[0], min(year_range[1], 2024))

if df.empty:
    st.error("No data found. Try clicking **Refresh Data** in the sidebar.")
    st.stop()

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
if st.session_state.show_predictions and year_range[1] > 2024:
    for code in countries:
        for indicator in [i for i in indicators if i != "gold_price"]:
            cdf = df[(df["country_code"] == code) & (df["indicator"] == indicator)]
            if not cdf.empty:
                pred = get_or_create_forecast(cdf, code, indicator)
                if not pred.empty:
                    predictions_dfs.append(pred)

    if "gold_price" in indicators:
        gold_df = df[df["indicator"] == "gold_price"]
        if not gold_df.empty:
            gold_pred = get_or_create_forecast(gold_df, "WLD", "gold_price")
            if not gold_pred.empty:
                predictions_dfs.append(gold_pred)

predictions_df = pd.concat(predictions_dfs, ignore_index=True) if predictions_dfs else pd.DataFrame()
st.session_state["current_df"] = df
st.session_state["predictions_df"] = predictions_df

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("## 📈 Dashboard")
st.caption(f"Showing {len(countries)} countries · {len(indicators)} indicators · {year_range[0]}–{year_range[1]}")
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

for indicator in indicators:
    ind_df = df[df["indicator"] == indicator]
    if ind_df.empty:
        continue

    # For gold_price, use WLD code
    if indicator == "gold_price":
        pred_df = predictions_df[predictions_df["indicator"] == "gold_price"] if not predictions_df.empty else pd.DataFrame()
        ind_df_plot = ind_df[ind_df["country_code"] == "WLD"]
    else:
        pred_df = predictions_df[predictions_df["country_code"].isin(countries)] if not predictions_df.empty else pd.DataFrame()
        ind_df_plot = ind_df[ind_df["country_code"].isin(countries)]

    fig = timeline_chart(ind_df_plot, pred_df, indicator, year_range)
    st.plotly_chart(fig, use_container_width=True)

# ── Anomaly Flags ─────────────────────────────────────────────────────────
st.divider()
st.markdown("#### 🚨 Anomaly Detection")
st.caption("Flagging unusual year-over-year changes (z-score > 2.5)")

anomaly_found = False
for code in countries:
    for indicator in [i for i in indicators if i != "gold_price"]:
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
