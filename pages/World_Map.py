"""
Page 5 — World Map: choropleth of economic indicators
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="World Map — EconVision", page_icon="🌍", layout="wide")

from utils.ui import inject_custom_css
inject_custom_css()
from utils.ui import render_sidebar
render_sidebar()

from utils.data_fetcher import get_all_countries, load_country_data, get_country_data_cached
from components.charts import indicator_label, format_value

# ── Load all countries for map ────────────────────────────────────────────
all_countries = get_all_countries()
all_codes = [c["code"] for c in all_countries]
country_map = {c["code"]: c["name"] for c in all_countries}

fullscreen = st.toggle("🗺️ Fullscreen Map View", value=False)
if fullscreen:
    st.markdown("""
    <style>
    [data-testid="stHeader"] {display: none;}
    .block-container {padding-top: 1.5rem !important; padding-bottom: 1.5rem !important;}
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("## 🌍 World Map")
    st.caption("Choropleth view of economic indicators across all available countries")
    st.divider()

year_range = st.session_state.get("year_range", (2000, 2026))

col1, col2, col3 = st.columns([1.5, 1.2, 1.2])
with col1:
    map_indicator = st.selectbox(
        "Indicator",
        options=["gdp", "gdp_per_capita", "debt_pct_gdp"],
        format_func=indicator_label,
        key="map_indicator",
    )
with col2:
    color_scale = st.selectbox(
        "Color Scale",
        ["Viridis", "Plasma", "RdYlGn", "Blues", "Reds", "Turbo"],
        index=2,
    )
with col3:
    projection_style = st.selectbox(
        "Projection",
        ["natural earth", "orthographic", "equirectangular", "mercator", "kavrayskiy7", "robinson"],
        index=0,
    )

# ── Load data for map (use cached session data + auto-load top countries) ─
@st.cache_data(ttl=3600, show_spinner="Loading world map data...")
def get_map_data(indicator: str, year_start: int, year_end: int) -> pd.DataFrame:
    """Get data for all countries for one indicator and year range."""
    from utils.database import fetch_economic_data
    df = fetch_economic_data(indicators=[indicator], year_start=year_start, year_end=year_end)
    return df

map_df = get_map_data(map_indicator, year_range[0], year_range[1])

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
        progress = st.progress(0, text="Loading countries…")
        total = len(TOP_40)
        for i, code in enumerate(TOP_40):
            name = country_map.get(code, code)
            progress.progress((i + 1) / total, text=f"Loading {name} ({i + 1}/{total})…")
            load_country_data(code, name)
        progress.empty()
        st.cache_data.clear()
        st.rerun()
else:
    # Sort by year to ensure animation frames are chronological
    year_df = map_df.sort_values(["year", "country_code"]).copy()

    selected_codes = st.session_state.get("selected_countries", [])
    if selected_codes:
        year_df = year_df[year_df["country_code"].isin(selected_codes)]

    if year_df.empty:
        st.warning(f"No data available for the selected range. Try different settings.")
    else:
        fig = px.choropleth(
            year_df,
            locations="country_code",
            locationmode="ISO-3",
            color="value",
            hover_name="country_name",
            hover_data={"value": ":.2f", "country_code": False},
            color_continuous_scale=color_scale,
            range_color=[year_df["value"].min(), year_df["value"].max()],
            title=f"{indicator_label(map_indicator)} — {year_range[0]} to {year_range[1]}",
            labels={"value": indicator_label(map_indicator)},
            animation_frame="year",
        )

        fig.update_geos(
            showcoastlines=True, coastlinecolor="#1E2740",
            showland=True, landcolor="#0A0E1A",
            showocean=True, oceancolor="#060A14",
            showlakes=True, lakecolor="#060A14",
            showframe=False,
            projection_type=projection_style,
        )
        fig.update_layout(
            height=800 if fullscreen else 560,
            paper_bgcolor="#111827",
            font=dict(color="#E2E8F0", family="monospace"),
            coloraxis_colorbar=dict(
                title=dict(text=indicator_label(map_indicator), font=dict(color="#E2E8F0")),
                tickfont=dict(color="#E2E8F0"),
                bgcolor="#111827",
            ),
            margin=dict(l=0, r=0, t=40, b=0),
        )
        
        # Style the animation controls if they exist
        if "sliders" in fig.layout:
            fig.layout.sliders[0].font.color = "#E2E8F0"
        if "updatemenus" in fig.layout:
            fig.layout.updatemenus[0].font.color = "#E2E8F0"

        st.plotly_chart(fig, use_container_width=True)

        if not fullscreen:
            # Stats
            latest_map_year = int(year_df["year"].max())
            metrics_df = year_df[year_df["year"] == latest_map_year]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(f"Countries with data ({latest_map_year})", len(metrics_df))
            if not metrics_df.empty:
                highest = metrics_df.sort_values('value', ascending=False).iloc[0]
                lowest = metrics_df.sort_values('value').iloc[0]
                c2.metric("Highest", f"{highest['country_name']} ({format_value(highest['value'], map_indicator)})")
                c3.metric("Lowest", f"{lowest['country_name']} ({format_value(lowest['value'], map_indicator)})")
                c4.metric("Global avg", format_value(metrics_df["value"].mean(), map_indicator))

            st.divider()
            st.markdown("### 🎲 3D Indicator Comparison")
            st.caption("Multivariate view of economic indicators over time for selected countries")
            
            current_df = st.session_state.get("current_df", pd.DataFrame())
            if not current_df.empty:
                pivot_df = current_df.pivot_table(
                    index=["country_code", "country_name", "year"],
                    columns="indicator",
                    values="value"
                ).reset_index()
                
                available_cols = pivot_df.columns.tolist()
                req_cols = [c for c in available_cols if c not in ["country_code", "country_name", "year"]]
                
                if len(req_cols) >= 3:
                    countries = pivot_df["country_name"].unique()
                    colors = px.colors.qualitative.Plotly
                    color_map = {c: colors[i % len(colors)] for i, c in enumerate(countries)}
                    
                    fig_3d = px.scatter_3d(
                        pivot_df.sort_values("year"),
                        x=req_cols[0],
                        y=req_cols[1],
                        z=req_cols[2],
                        color="country_name",
                        color_discrete_map=color_map,
                        text="country_name",
                        animation_frame="year",
                        animation_group="country_name",
                        hover_name="country_name",
                        hover_data={"year": True},
                        labels={
                            req_cols[0]: indicator_label(req_cols[0]),
                            req_cols[1]: indicator_label(req_cols[1]),
                            req_cols[2]: indicator_label(req_cols[2]),
                        },
                    )
                    
                    # Add chronological lines connecting points for each country's historical path
                    for country in countries:
                        cdf = pivot_df[pivot_df["country_name"] == country].sort_values("year")
                        fig_3d.add_trace(go.Scatter3d(
                            x=cdf[req_cols[0]],
                            y=cdf[req_cols[1]],
                            z=cdf[req_cols[2]],
                            mode="lines",
                            line=dict(color=color_map[country], width=2),
                            name=f"{country} Path",
                            showlegend=False,
                            hoverinfo="skip"
                        ))

                    fig_3d.update_traces(
                        marker=dict(size=6, opacity=0.9),
                        textposition="top center",
                        textfont=dict(size=10, color="#E2E8F0"),
                        selector=dict(type="scatter3d", mode="markers+text")
                    )
                    fig_3d.update_layout(
                        height=600,
                        paper_bgcolor="#111827",
                        plot_bgcolor="#0A0E1A",
                        font=dict(color="#E2E8F0", family="monospace"),
                        margin=dict(l=0, r=0, t=20, b=0),
                        scene=dict(
                            xaxis=dict(gridcolor="#1E2740", backgroundcolor="#0A0E1A"),
                            yaxis=dict(gridcolor="#1E2740", backgroundcolor="#0A0E1A"),
                            zaxis=dict(gridcolor="#1E2740", backgroundcolor="#0A0E1A"),
                        )
                    )
                    # Style the generated animation slider and play buttons to match the dark theme
                    if "sliders" in fig_3d.layout:
                        fig_3d.layout.sliders[0].font.color = "#E2E8F0"
                    if "updatemenus" in fig_3d.layout:
                        for um in fig_3d.layout.updatemenus:
                            um.font.color = "#E2E8F0"
                            um.bgcolor = "#1E2740"
                            um.bordercolor = "#0A0E1A"
                    st.plotly_chart(fig_3d, use_container_width=True)
                else:
                    st.info("Load at least 3 indicators in the sidebar to see the 3D scatter plot.")
            else:
                st.info("No data loaded. Use the Dashboard to load countries and indicators.")
