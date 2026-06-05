"""
Reusable Plotly chart components.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime

COLORS = [
    "#00D4FF", "#FF6B6B", "#4ECDC4", "#FFE66D",
    "#A8E6CF", "#FF8B94", "#B4A7D6", "#F9C784",
    "#95E1D3", "#F38181", "#AA96DA", "#FCBAD3",
]

BG = "#0A0E1A"
GRID = "#1E2740"
TEXT = "#E2E8F0"
PAPER_BG = "#111827"


def base_layout(title: str = "", height: int = 420) -> dict:
    return dict(
        title=dict(text=title, font=dict(color=TEXT, size=16, family="monospace"), x=0.02),
        height=height,
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=BG,
        font=dict(color=TEXT, family="monospace"),
        xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
        yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
        legend=dict(bgcolor="rgba(0,0,0,0.3)", bordercolor=GRID, font=dict(color=TEXT)),
        margin=dict(l=60, r=20, t=50, b=40),
        hovermode="x unified",
    )


def indicator_label(indicator: str) -> str:
    labels = {
        "gdp": "GDP (USD)",
        "gdp_per_capita": "GDP Per Capita (USD)",
        "debt_pct_gdp": "Debt (% of GDP)",
        "gold_price": "Gold Price (USD/oz)",
        "inflation": "Inflation (%)",
        "unemployment": "Unemployment (%)",
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

    # Add vertical line at current year
    current_year = datetime.now().year
    fig.add_vline(x=current_year, line_dash="dot", line_color="#666", annotation_text="Now", annotation_font_color="#999")

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
    return fig


def health_score_gauge(score: float, country_name: str) -> go.Figure:
    """Gauge chart for economic health score."""
    color = "#FF6B6B" if score < 40 else "#FFE66D" if score < 65 else "#4ECDC4"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": f"{country_name}", "font": {"color": TEXT, "size": 13}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": TEXT},
            "bar": {"color": color},
            "bgcolor": BG,
            "bordercolor": GRID,
            "steps": [
                {"range": [0, 40], "color": "rgba(255,107,107,0.15)"},
                {"range": [40, 65], "color": "rgba(255,230,109,0.15)"},
                {"range": [65, 100], "color": "rgba(78,205,196,0.15)"},
            ],
        },
        number={"font": {"color": TEXT, "size": 28}},
    ))
    fig.update_layout(
        height=200,
        paper_bgcolor=PAPER_BG,
        font=dict(color=TEXT),
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


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
