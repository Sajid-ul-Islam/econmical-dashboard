"""
Page 5 — World Map: choropleth of economic indicators
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="World Map — EconVision", page_icon="🌍", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

from utils.data_fetcher import get_all_countries, load_country_data, get_country_data_cached
from components.charts import indicator_label, format_value

# ── Load all countries for map ────────────────────────────────────────────
all_countries = get_all_countries()
all_codes = [c["code"] for c in all_countries]
country_map = {c["code"]: c["name"] for c in all_countries}

st.markdown("## 🌍 World Map")
st.caption("Choropleth view of economic indicators across all available countries")
st.divider()

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    map_indicator = st.selectbox(
        "Indicator",
        options=["gdp", "gdp_per_capita", "debt_pct_gdp"],
        format_func=indicator_label,
        key="map_indicator",
    )
with col2:
    map_year = st.slider("Year", 1995, 2024, 2022, key="map_year")
with col3:
    color_scale = st.selectbox(
        "Color Scale",
        ["Viridis", "Plasma", "RdYlGn", "Blues", "Reds", "Turbo"],
        index=2,
    )

# ── Load data for map (use cached session data + auto-load top countries) ─
@st.cache_data(ttl=3600, show_spinner="Loading world map data...")
def get_map_data(indicator: str, year: int) -> pd.DataFrame:
    """Get data for all countries for one indicator/year."""
    from utils.database import fetch_economic_data
    df = fetch_economic_data(indicators=[indicator], year_start=year, year_end=year)
    return df

map_df = get_map_data(map_indicator, map_year)

if map_df.empty:
    st.info("No map data loaded yet. Go to the Dashboard page first and load some countries, then return here.")

    # Offer to load default set
    if st.button("🌍 Load Top 40 Economies for Map"):
        TOP_40 = [
            "USA","CHN","DEU","JPN","GBR","FRA","IND","ITA","BRA","CAN",
            "RUS","KOR","AUS","ESP","MEX","IDN","NLD","SAU","TUR","CHE",
            "POL","SWE","BEL","ARG","NOR","AUT","UAE","NGA","ZAF","EGY",
            "BGD","PAK","VNM","THA","PHL","MYS","COL","CHL","FIN","DNK",
        ]
        with st.spinner("Loading 40 countries..."):
            for code in TOP_40:
                name = country_map.get(code, code)
                load_country_data(code, name)
        st.cache_data.clear()
        st.rerun()
else:
    # Filter to selected year and deduplicate
    year_df = map_df[map_df["year"] == map_year].drop_duplicates(subset=["country_code"])

    if year_df.empty:
        st.warning(f"No data available for {map_year}. Try a different year.")
    else:
        fig = px.choropleth(
            year_df,
            locations="country_code",
            locationmode="ISO-3",
            color="value",
            hover_name="country_name",
            hover_data={"value": ":.2f", "country_code": False},
            color_continuous_scale=color_scale,
            title=f"{indicator_label(map_indicator)} — {map_year}",
            labels={"value": indicator_label(map_indicator)},
        )

        fig.update_geos(
            showcoastlines=True, coastlinecolor="#1E2740",
            showland=True, landcolor="#0A0E1A",
            showocean=True, oceancolor="#060A14",
            showlakes=True, lakecolor="#060A14",
            showframe=False,
            projection_type="natural earth",
        )
        fig.update_layout(
            height=560,
            paper_bgcolor="#111827",
            font=dict(color="#E2E8F0", family="monospace"),
            coloraxis_colorbar=dict(
                title=dict(text=indicator_label(map_indicator), font=dict(color="#E2E8F0")),
                tickfont=dict(color="#E2E8F0"),
                bgcolor="#111827",
            ),
            margin=dict(l=0, r=0, t=40, b=0),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Stats
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Countries with data", len(year_df))
        c2.metric("Highest", f"{year_df.sort_values('value', ascending=False).iloc[0]['country_name']} ({format_value(year_df['value'].max(), map_indicator)})")
        c3.metric("Lowest", f"{year_df.sort_values('value').iloc[0]['country_name']} ({format_value(year_df['value'].min(), map_indicator)})")
        c4.metric("Global avg", format_value(year_df["value"].mean(), map_indicator))
