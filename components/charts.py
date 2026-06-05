"""
Reusable Plotly chart components.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

COLORS = [
    "#00D4FF", "#FF6B6B", "#4ECDC4", "#FFE66D",
    "#A8E6CF", "#FF8B94", "#B4A7D6", "#F9C784",
    "#95E1D3", "#F38181", "#AA96DA", "#FCBAD3",
]

# ── Debt risk classification ──────────────────────────────────────────────
DEBT_COLOR_MAP = {
    "Critical (>200%)":  "#8b0000",
    "High (>90%)":       "#d32f2f",
    "Elevated (60–90%)": "#f57c00",
    "Moderate (30–60%)": "#388e3c",
    "Low (<30%)":        "#2ecc71",
}

def classify_debt(ratio: float) -> str:
    """Return a debt risk tier label for a given debt-to-GDP ratio."""
    if ratio > 200:
        return "Critical (>200%)"
    elif ratio > 90:
        return "High (>90%)"
    elif ratio > 60:
        return "Elevated (60–90%)"
    elif ratio > 30:
        return "Moderate (30–60%)"
    return "Low (<30%)"

HISTORICAL_EVENTS = [
    {"year": 1971, "label": "Nixon Shock", "description": "End of Bretton Woods, USD no longer backed by gold."},
    {"year": 1974, "label": "Petrodollar", "description": "OPEC agrees to price oil in USD, increasing its global demand."},
    {"year": 1985, "label": "Plaza Accord", "description": "Agreement to devalue the U.S. dollar vs yen and Mark."},
    {"year": 1997, "label": "Asian Crisis", "description": "Asian Financial Crisis begins in Thailand."},
    {"year": 2000, "label": "Dot-com Burst", "description": "Collapse of the dot-com technology bubble."},
    {"year": 2008, "label": "GFC", "description": "Global Financial Crisis, major housing and banking collapse."},
    {"year": 2011, "label": "EU Debt Crisis", "description": "European sovereign debt crisis."},
    {"year": 2020, "label": "COVID-19", "description": "Global pandemic leads to widespread economic shutdowns."},
]


def base_layout(title: str = "", height: int = 420) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=16, family="monospace"), x=0.02),
        height=height,
        margin=dict(l=60, r=20, t=50, b=40),
        hovermode="x unified",
        template="streamlit",
    )


def indicator_label(indicator: str) -> str:
    labels = {
        "gdp": "GDP (USD)",
        "gdp_per_capita": "GDP Per Capita (USD)",
        "debt_pct_gdp": "Debt (% of GDP)",
        "gold_price": "Gold Price (USD/oz)",
        "inflation": "Inflation (%)",
        "unemployment": "Unemployment (%)",
        "dxy": "US Dollar Index (DXY)",
        "life_expectancy": "Life Expectancy (Years)",
        "silver_price": "Silver Price (USD/oz)",
        "oil_price": "Oil Price (USD/bbl)",
    }
    return labels.get(indicator, indicator.replace("_", " ").title())


def format_value(value: float, indicator: str) -> str:
    if indicator == "gdp":
        if value >= 1e12:
            return f"${value/1e12:.2f}T"
        elif value >= 1e9:
            return f"${value/1e9:.1f}B"
        return f"${value:,.0f}"
    elif indicator == "gdp_per_capita":
        return f"${value:,.0f}"
    elif indicator == "debt_pct_gdp":
        return f"{value:.1f}%"
    elif indicator in ["inflation", "unemployment"]:
        return f"{value:.1f}%"
    elif indicator == "gold_price":
        return f"${value:,.0f}/oz"
    elif indicator == "oil_price":
        return f"${value:,.2f}/bbl"
    elif indicator == "dxy":
        return f"{value:.2f}"
    elif indicator == "silver_price":
        return f"${value:,.2f}/oz"
    elif indicator == "life_expectancy":
        return f"{value:.1f} yrs"
    return f"{value:,.2f}"


def timeline_chart(
    historical_df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    indicator: str,
    year_range: tuple,
) -> go.Figure:
    """Multi-country timeline with forecast bands."""
    fig = go.Figure()

    if historical_df.empty:
        fig.update_layout(**base_layout(f"{indicator_label(indicator)} — No Data"))
        return fig

    countries = historical_df["country_code"].unique()
    color_map = {c: COLORS[i % len(COLORS)] for i, c in enumerate(countries)}

    for country in countries:
        cdf = historical_df[
            (historical_df["country_code"] == country) &
            (historical_df["indicator"] == indicator)
        ].sort_values("year")
        cdf = cdf[(cdf["year"] >= year_range[0]) & (cdf["year"] <= year_range[1])]

        if cdf.empty:
            continue

        cname = cdf["country_name"].iloc[0] if "country_name" in cdf.columns else country
        color = color_map[country]

        # Historical line
        fig.add_trace(go.Scatter(
            x=cdf["year"], y=cdf["value"],
            name=cname,
            line=dict(color=color, width=2.5),
            hovertemplate=f"<b>{cname}</b><br>Year: %{{x}}<br>{indicator_label(indicator)}: %{{customdata}}<extra></extra>",
            customdata=[format_value(v, indicator) for v in cdf["value"]],
            mode="lines+markers",
            marker=dict(size=4),
        ))

        # Forecast
        if not predictions_df.empty:
            pdf = predictions_df[
                (predictions_df["country_code"] == country) &
                (predictions_df["indicator"] == indicator)
            ].sort_values("year")

            if not pdf.empty:
                # Confidence band
                fig.add_trace(go.Scatter(
                    x=pd.concat([pdf["year"], pdf["year"][::-1]]),
                    y=pd.concat([pdf["upper_bound"], pdf["lower_bound"][::-1]]),
                    fill="toself",
                    fillcolor=f"rgba{tuple(list(_hex_to_rgb(color)) + [0.15])}",
                    line=dict(color="rgba(0,0,0,0)"),
                    showlegend=False,
                    hoverinfo="skip",
                    name=f"{cname} CI",
                ))
                # Forecast line
                fig.add_trace(go.Scatter(
                    x=pdf["year"], y=pdf["predicted"],
                    name=f"{cname} (forecast)",
                    line=dict(color=color, width=2, dash="dash"),
                    hovertemplate=f"<b>{cname} Forecast</b><br>Year: %{{x}}<br>{indicator_label(indicator)}: %{{customdata}}<extra></extra>",
                    customdata=[format_value(v, indicator) for v in pdf["predicted"]],
                ))

    add_event_annotations(fig, year_range)
    layout = base_layout(indicator_label(indicator), height=450)
    layout["xaxis"]["title"] = "Year"
    layout["yaxis"]["title"] = indicator_label(indicator)
    fig.update_layout(**layout)
    return fig


def comparison_bar(
    df: pd.DataFrame,
    indicator: str,
    year: int,
    ascending: bool = True,
) -> go.Figure:
    """Side-by-side bar for country comparison at a given year."""
    filtered = df[
        (df["indicator"] == indicator) & (df["year"] == year)
    ].sort_values("value", ascending=ascending)

    if filtered.empty:
        fig = go.Figure()
        fig.update_layout(**base_layout(f"No data for {year}"))
        return fig

    colors = [COLORS[i % len(COLORS)] for i in range(len(filtered))]
    cnames = filtered["country_name"] if "country_name" in filtered.columns else filtered["country_code"]

    fig = go.Figure(go.Bar(
        x=filtered["value"],
        y=cnames,
        orientation="h",
        marker=dict(color=colors),
        hovertemplate="%{y}: %{customdata}<extra></extra>",
        customdata=[format_value(v, indicator) for v in filtered["value"]],
    ))

    layout = base_layout(f"{indicator_label(indicator)} Comparison — {year}", height=max(300, len(filtered) * 45))
    layout["xaxis"]["title"] = indicator_label(indicator)
    fig.update_layout(**layout)

    # Debt reference lines — Maastricht 60% limit and 90% high-risk threshold
    if indicator == "debt_pct_gdp":
        fig.add_vline(
            x=60, line_dash="dash", line_color="#f57c00",
            annotation_text="Maastricht 60%", annotation_font_color="#f57c00",
            annotation_position="top",
        )
        fig.add_vline(
            x=90, line_dash="dash", line_color="#d32f2f",
            annotation_text="High Risk 90%", annotation_font_color="#d32f2f",
            annotation_position="top",
        )

    return fig


def health_score_gauge(score: float, country_name: str) -> go.Figure:
    """Gauge chart for economic health score."""
    color = "#FF6B6B" if score < 40 else "#FFE66D" if score < 65 else "#4ECDC4"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": f"{country_name}", "font": {"size": 13}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 40], "color": "rgba(255,107,107,0.15)"},
                {"range": [40, 65], "color": "rgba(255,230,109,0.15)"},
                {"range": [65, 100], "color": "rgba(78,205,196,0.15)"},
            ],
        },
        number={"font": {"size": 28}},
    ))
    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig


def correlation_heatmap(df: pd.DataFrame, indicator1: str, indicator2: str) -> go.Figure:
    """Correlation scatter between two indicators across countries, colored by country."""
    countries = df["country_code"].unique()
    color_map = {c: COLORS[i % len(COLORS)] for i, c in enumerate(countries)}

    fig = go.Figure()

    for country in countries:
        cdf = df[df["country_code"] == country]
        cname = cdf["country_name"].iloc[0] if "country_name" in cdf.columns else country
        ind1 = cdf[cdf["indicator"] == indicator1][["year", "value"]].rename(columns={"value": "v1"})
        ind2 = cdf[cdf["indicator"] == indicator2][["year", "value"]].rename(columns={"value": "v2"})
        merged = pd.merge(ind1, ind2, on="year")
        if merged.empty:
            continue

        labels = [f"{cname} {int(r['year'])}" for _, r in merged.iterrows()]
        fig.add_trace(go.Scatter(
            x=merged["v1"],
            y=merged["v2"],
            mode="markers",
            name=cname,
            marker=dict(color=color_map[country], size=6, opacity=0.75),
            text=labels,
            hovertemplate="%{text}<br>"
                          f"{indicator_label(indicator1)}: %{{x}}<br>"
                          f"{indicator_label(indicator2)}: %{{y}}<extra></extra>",
        ))

    layout = base_layout(f"{indicator_label(indicator1)} vs {indicator_label(indicator2)}", height=420)
    layout["xaxis"]["title"] = indicator_label(indicator1)
    layout["yaxis"]["title"] = indicator_label(indicator2)
    fig.update_layout(**layout)
    return fig


def add_event_annotations(fig: go.Figure, year_range: tuple):
    """Adds vertical lines and annotations for key historical events and 'Now'."""
    # Add 'Now' line first
    now_year = datetime.now().year
    if year_range[0] <= now_year <= year_range[1]:
        fig.add_vline(
            x=now_year, line_dash="dot", line_color="gray",
            annotation_text="Now", annotation_font_color="gray",
            annotation_position="top",
            annotation_hovertext="Current Year"
        )

    # Add historical events
    visible_events = [e for e in HISTORICAL_EVENTS if year_range[0] <= e["year"] <= year_range[1]]
    
    for i, event in enumerate(visible_events):
        position = "bottom" if i % 2 == 0 else "top"
        if event["year"] == now_year:
            position = "bottom"

        fig.add_vline(
            x=event["year"], line_width=1, line_dash="dot",
            line_color="rgba(128, 128, 128, 0.5)", annotation_text=event["label"],
            annotation_position=position, annotation_font=dict(size=10, color="rgba(128, 128, 128, 0.8)"),
            annotation_bgcolor="rgba(240, 240, 240, 0.5)",
            annotation_hovertext=event["description"]
        )

def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
