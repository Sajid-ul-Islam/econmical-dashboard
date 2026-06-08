"""
Page 2 — Compare: bar charts, correlation, what-if simulator
"""

import streamlit as st
import pandas as pd
import numpy as np

from utils.ui import render_sidebar
render_sidebar()

from utils.data_fetcher import get_country_data_cached, get_all_countries
from components.charts import comparison_bar, correlation_heatmap, format_value, indicator_label

# ── Load ──────────────────────────────────────────────────────────────────
countries = st.session_state.get("selected_countries", ["USA", "CHN", "DEU"])
indicators = st.session_state.get("selected_indicators", ["gdp", "gdp_per_capita", "debt_pct_gdp"])
year_range = st.session_state.get("year_range", (2000, 2026))

all_countries_list = get_all_countries()
country_map = {c["code"]: c["name"] for c in all_countries_list}

df = st.session_state.get("current_df", pd.DataFrame())
if df.empty:
    with st.spinner("Loading data..."):
        df = get_country_data_cached(countries, indicators, year_range[0], min(year_range[1], 2026))
        st.session_state["current_df"] = df

predictions_df = st.session_state.get("predictions_df", pd.DataFrame())

# ── Group detection ───────────────────────────────────────────────────────
_GROUPS = {
    "NATO":       ["ALB","BEL","BGR","CAN","HRV","CZE","DNK","EST","FIN","FRA","DEU","GRC","HUN","ISL","ITA","LVA","LTU","LUX","MNE","MKD","NLD","NOR","POL","PRT","ROU","SVK","SVN","ESP","SWE","TUR","GBR","USA"],
    "EU":         ["AUT","BEL","BGR","HRV","CYP","CZE","DNK","EST","FIN","FRA","DEU","GRC","HUN","IRL","ITA","LVA","LTU","LUX","MLT","NLD","POL","PRT","ROU","SVK","SVN","ESP","SWE"],
    "BRICS":      ["BRA","RUS","IND","CHN","ZAF","EGY","ETH","IRN","ARE","SAU"],
    "SAARC":      ["AFG","BGD","BTN","IND","MDV","NPL","PAK","LKA"],
    "G7":         ["CAN","FRA","DEU","ITA","JPN","GBR","USA"],
    "G20":        ["ARG","AUS","BRA","CAN","CHN","FRA","DEU","IND","IDN","ITA","JPN","KOR","MEX","RUS","SAU","ZAF","TUR","GBR","USA"],
    "OPEC":       ["DZA","AGO","COG","GNQ","GAB","IRN","IRQ","KWT","LBY","NGA","SAU","ARE","VEN"],
    "Arab League":["DZA","BHR","COM","DJI","EGY","IRQ","JOR","KWT","LBN","LBY","MRT","MAR","OMN","PSE","QAT","SAU","SOM","SDN","SYR","TUN","ARE","YEM"],
    "OIC":        ["AFG","ALB","DZA","AGO","BHR","BGD","BEN","BFA","BRN","CMR","TCD","COM","CIV","DJI","EGY","GAB","GMB","GIN","GNB","GUY","IDN","IRN","IRQ","JOR","KAZ","KWT","KGZ","LBN","LBY","MYS","MDV","MLI","MRT","MAR","MOZ","NER","NGA","OMN","PAK","PSE","QAT","SAU","SEN","SLE","SOM","SDN","SUR","SYR","TJK","TGO","TUN","TUR","TKM","UGA","ARE","UZB","YEM"],
}

def _detect_group(codes: list) -> str | None:
    if len(codes) < 3:
        return None
    code_set = set(codes)
    for name, members in _GROUPS.items():
        if code_set.issubset(set(members)):
            return name
    return None

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("## 🔍 Country Comparison")
st.caption("Bar charts, correlation explorer, and what-if simulator")

# Group detection banner
detected_group = _detect_group(countries)
if detected_group:
    st.info(f"📊 Viewing **{detected_group}** member economies · {len(countries)} countries selected")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Bar Comparison", "🔗 Correlation", "📐 Ranking Table", "🧪 What-If Simulator"])

# ── Tab 1: Bar Charts ─────────────────────────────────────────────────────
with tab1:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        bar_indicator = st.selectbox(
            "Indicator",
            options=indicators,
            format_func=indicator_label,
            key="bar_indicator",
        )
    with col_b:
        available_years = sorted(df["year"].unique(), reverse=True)
        
        # Default to the most recent year where ALL selected countries have data
        best_year = available_years[0] if available_years else 2024
        if not df.empty and bar_indicator:
            ind_df = df[(df["country_code"].isin(countries)) & (df["indicator"] == bar_indicator)]
            year_counts = ind_df.groupby("year")["country_code"].nunique()
            complete_years = year_counts[year_counts == len(countries)].index.tolist()
            if complete_years:
                best_year = max(complete_years)
        default_idx = available_years.index(best_year) if best_year in available_years else 0
        
        bar_year = st.selectbox("Year", options=available_years[:20], index=default_idx, key="bar_year")

    if not df.empty and bar_indicator:
        bar_ascending = st.session_state.get("sort_order", "Highest to Lowest") == "Highest to Lowest"
        fig = comparison_bar(df[df["country_code"].isin(countries)], bar_indicator, bar_year, ascending=bar_ascending)
        st.plotly_chart(fig, use_container_width=True)

        # Top/bottom callouts
        snap = df[
            (df["country_code"].isin(countries)) &
            (df["indicator"] == bar_indicator) &
            (df["year"] == bar_year)
        ].sort_values("value", ascending=False)

        if len(snap) >= 2:
            c1, c2 = st.columns(2)
            with c1:
                top = snap.iloc[0]
                cname = top["country_name"] if "country_name" in top else top["country_code"]
                st.success(f"🥇 **Highest**: {cname} — {format_value(top['value'], bar_indicator)}")
            with c2:
                bot = snap.iloc[-1]
                cname = bot["country_name"] if "country_name" in bot else bot["country_code"]
                st.info(f"🔻 **Lowest**: {cname} — {format_value(bot['value'], bar_indicator)}")

# ── Tab 2: Correlation ────────────────────────────────────────────────────
with tab2:
    st.markdown("Explore relationship between two economic indicators across all selected countries and years.")
    col_x, col_y = st.columns(2)
    with col_x:
        ind_x = st.selectbox("X-Axis Indicator", options=indicators, format_func=indicator_label, key="corr_x")
    with col_y:
        other_inds = [i for i in indicators if i != ind_x]
        ind_y_default = other_inds[0] if other_inds else indicators[0]
        ind_y = st.selectbox(
            "Y-Axis Indicator",
            options=indicators,
            index=indicators.index(ind_y_default) if ind_y_default in indicators else 0,
            format_func=indicator_label,
            key="corr_y",
        )

    if ind_x != ind_y and not df.empty:
        fig = correlation_heatmap(df[df["country_code"].isin(countries)], ind_x, ind_y)
        st.plotly_chart(fig, use_container_width=True)

        # Correlation coefficient
        countries_overlap = df["country_code"].unique()
        x_vals, y_vals = [], []
        for code in countries_overlap:
            cdf = df[df["country_code"] == code]
            i1 = cdf[cdf["indicator"] == ind_x][["year", "value"]].rename(columns={"value": "v1"})
            i2 = cdf[cdf["indicator"] == ind_y][["year", "value"]].rename(columns={"value": "v2"})
            merged = pd.merge(i1, i2, on="year")
            x_vals.extend(merged["v1"].tolist())
            y_vals.extend(merged["v2"].tolist())

        if len(x_vals) > 3:
            corr = np.corrcoef(x_vals, y_vals)[0, 1]
            strength = "strong" if abs(corr) > 0.7 else "moderate" if abs(corr) > 0.4 else "weak"
            direction = "positive" if corr > 0 else "negative"
            st.metric("Pearson Correlation", f"{corr:.3f}", f"{strength} {direction} relationship")
    else:
        st.info("Select two different indicators to see correlation.")

# ── Tab 3: Ranking Table ──────────────────────────────────────────────────
with tab3:
    rank_indicator = st.selectbox("Rank by", options=indicators, format_func=indicator_label, key="rank_ind")
    available_years = sorted(df["year"].unique(), reverse=True)
    
    best_year_rank = available_years[0] if available_years else 2024
    if not df.empty and rank_indicator:
        ind_df_rank = df[(df["country_code"].isin(countries)) & (df["indicator"] == rank_indicator)]
        year_counts_rank = ind_df_rank.groupby("year")["country_code"].nunique()
        complete_years_rank = year_counts_rank[year_counts_rank == len(countries)].index.tolist()
        if complete_years_rank:
            best_year_rank = max(complete_years_rank)
    default_idx_rank = available_years.index(best_year_rank) if best_year_rank in available_years else 0
    
    rank_year = st.selectbox("Year", options=available_years[:20], index=default_idx_rank, key="rank_year")

    rank_ascending = st.session_state.get("sort_order", "Highest to Lowest") == "Lowest to Highest"
    rank_df = df[
        (df["country_code"].isin(countries)) &
        (df["indicator"] == rank_indicator) &
        (df["year"] == rank_year)
    ].copy().sort_values("value", ascending=rank_ascending)

    if not rank_df.empty:
        rank_df["Rank"] = range(1, len(rank_df) + 1)
        rank_df["Country"] = rank_df.apply(
            lambda r: r["country_name"] if "country_name" in r and pd.notna(r["country_name"]) else r["country_code"],
            axis=1
        )
        rank_df["Value"] = rank_df.apply(lambda r: format_value(r["value"], rank_indicator), axis=1)

        # Add YoY
        prev_year = rank_year - 1
        prev_df = df[
            (df["country_code"].isin(countries)) &
            (df["indicator"] == rank_indicator) &
            (df["year"] == prev_year)
        ].set_index("country_code")["value"]

        def yoy(row):
            prev = prev_df.get(row["country_code"])
            if prev and prev != 0:
                return f"{((row['value'] - prev) / abs(prev)) * 100:+.1f}%"
            return "—"

        rank_df["YoY Change"] = rank_df.apply(yoy, axis=1)

        display_df = rank_df[["Rank", "Country", "Value", "YoY Change"]].reset_index(drop=True)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ Download CSV",
            data=rank_df[["country_code", "Country", "year", "value"]].to_csv(index=False),
            file_name=f"econvision_{rank_indicator}_{rank_year}.csv",
            mime="text/csv",
        )

# ── Tab 4: What-If Simulator ──────────────────────────────────────────────
with tab4:
    st.markdown("**Adjust parameters and see projected economic outcomes.**")
    st.caption("Uses a simplified growth model — for illustration and scenario analysis.")

    col1, col2 = st.columns([1, 2])

    with col1:
        sim_country = st.selectbox(
            "Country",
            options=countries,
            format_func=lambda c: country_map.get(c, c),
            key="sim_country",
        )
        gdp_growth_adj = st.slider("Annual GDP Growth (%)", -5.0, 15.0, 3.0, 0.1)
        debt_change = st.slider("Debt Change per Year (pp)", -10.0, 10.0, 0.0, 0.5)
        years_forward = st.slider("Years to Project", 5, 20, 10)
        show_scenario = st.toggle("Show What-If Scenario", value=True)

    with col2:
        # Get latest GDP for this country
        base_df = df[
            (df["country_code"] == sim_country) &
            (df["indicator"] == "gdp")
        ].sort_values("year")

        base_debt_df = df[
            (df["country_code"] == sim_country) &
            (df["indicator"] == "debt_pct_gdp")
        ].sort_values("year")

        if not base_df.empty:
            base_gdp = base_df["value"].iloc[-1]
            base_year = int(base_df["year"].iloc[-1])
            cname = country_map.get(sim_country, sim_country)

            proj_years = list(range(base_year + 1, base_year + years_forward + 1))
            proj_gdp = [base_gdp * ((1 + gdp_growth_adj / 100) ** i) for i in range(1, years_forward + 1)]

            base_debt = base_debt_df["value"].iloc[-1] if not base_debt_df.empty else 60
            proj_debt = [max(0, base_debt + debt_change * i) for i in range(1, years_forward + 1)]

            import plotly.graph_objects as go
            from components.charts import base_layout
            from utils.forecasting import get_or_create_forecasts_batch

            ml_pred = get_or_create_forecasts_batch(base_df, [sim_country], ["gdp"])
            ml_debt_pred = get_or_create_forecasts_batch(base_debt_df, [sim_country], ["debt_pct_gdp"]) if not base_debt_df.empty else pd.DataFrame()

            fig = go.Figure()
            # Historical GDP
            fig.add_trace(go.Scatter(
                x=base_df["year"], y=base_df["value"],
                name="Historical", line=dict(color="#00D4FF", width=2),
                mode="lines+markers", marker=dict(size=4),
            ))
            # ML Baseline Forecast
            show_preds = st.session_state.get("show_predictions", True)
            if show_preds and not ml_pred.empty:
                ml_pred_plot = ml_pred[ml_pred["year"].isin(proj_years)]
                fig.add_trace(go.Scatter(
                    x=ml_pred_plot["year"], y=ml_pred_plot["predicted"],
                    name="ML Baseline (Prophet)", line=dict(color="#FFE66D", width=2, dash="dot"),
                ))
            
            if show_scenario:
                # Projected GDP
                fig.add_trace(go.Scatter(
                    x=proj_years, y=proj_gdp,
                    name="What-If Scenario", line=dict(color="#4ECDC4", width=2.5, dash="dash"),
                ))
            
            layout = base_layout(f"{cname} — GDP {'What-If vs ' if show_scenario else ''}ML Baseline")
            layout.setdefault("xaxis", {})["title"] = "Year"
            layout.setdefault("yaxis", {})["title"] = "GDP (USD)"
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

            final_gdp = proj_gdp[-1]
            final_debt = proj_debt[-1]
            
            ml_final_gdp = ml_pred[ml_pred["year"] == proj_years[-1]]["predicted"].values[0] if not ml_pred.empty and proj_years[-1] in ml_pred["year"].values else None
            ml_final_debt = ml_debt_pred[ml_debt_pred["year"] == proj_years[-1]]["predicted"].values[0] if not ml_debt_pred.empty and proj_years[-1] in ml_debt_pred["year"].values else None

            c_a, c_b, c_c = st.columns(3)
            
            gdp_delta = f"vs ML Baseline: {((final_gdp - ml_final_gdp) / ml_final_gdp * 100):+.1f}%" if ml_final_gdp else f"in {base_year + years_forward}"
            debt_delta = f"vs ML Baseline: {(final_debt - ml_final_debt):+.1f}pp" if ml_final_debt else f"{final_debt - base_debt:+.1f}pp"
            
            c_a.metric("Scenario GDP", format_value(final_gdp, "gdp"), gdp_delta)
            c_b.metric("Scenario Debt Ratio", f"{final_debt:.1f}%", debt_delta, delta_color="inverse")
            c_c.metric("Growth Multiplier", f"{final_gdp / base_gdp:.2f}x", f"over {years_forward} years")
        else:
            st.info("No GDP data available for the selected country.")
