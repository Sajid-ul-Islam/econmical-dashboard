"""
Page 6 — Macro Trends: USD purchasing power erosion & precious metals comparison
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Macro Trends — EconVision", page_icon="📉", layout="wide")

from utils.ui import inject_custom_css, render_sidebar
inject_custom_css()
render_sidebar()

# ── Constants ─────────────────────────────────────────────────────────────# US CPI inflation by year (annual %, BLS data)
US_INFLATION = {
    1970: 5.8,  1971: 4.3,  1972: 3.3,  1973: 6.2,  1974: 11.1,
    1975: 9.1,  1976: 5.8,  1977: 6.5,  1978: 7.6,  1979: 11.3,
    1980: 13.5, 1981: 10.3, 1982: 6.2,  1983: 3.2,  1984: 4.3,
    1985: 3.6,  1986: 1.9,  1987: 3.6,  1988: 4.1,  1989: 4.8,
    1990: 5.4,  1991: 4.2,  1992: 3.0,  1993: 3.0,  1994: 2.6,
    1995: 2.8,  1996: 3.0,  1997: 2.3,  1998: 1.6,  1999: 2.2,
    2000: 3.4,  2001: 2.8,  2002: 1.6,  2003: 2.3,  2004: 2.7,
    2005: 3.4,  2006: 3.2,  2007: 2.9,  2008: 3.8,  2009: -0.4,
    2010: 1.6,  2011: 3.2,  2012: 2.1,  2013: 1.5,  2014: 1.6,
    2015: 0.1,  2016: 1.3,  2017: 2.1,  2018: 2.4,  2019: 1.8,
    2020: 1.2,  2021: 4.7,  2022: 8.0,  2023: 4.1,  2024: 2.9,
}

# Gold & silver prices USD/oz
GOLD_PRICES = {
    1970: 36.0,  1971: 40.8,  1972: 58.4,  1973: 97.3,  1974: 154.0,
    1975: 160.9, 1976: 124.8, 1977: 147.8, 1978: 193.4, 1979: 306.7,
    1980: 614.9, 1981: 459.8, 1982: 375.9, 1983: 424.4, 1984: 360.5,
    1985: 317.2, 1986: 367.9, 1987: 446.5, 1988: 436.9, 1989: 381.4,
    1990: 383.5, 1991: 362.1, 1992: 344.7, 1993: 359.8, 1994: 384.0,
    1995: 384.1, 1996: 387.7, 1997: 331.0, 1998: 294.2, 1999: 278.9,
    2000: 279.1, 2001: 271.0, 2002: 309.7, 2003: 363.4, 2004: 409.2,
    2005: 444.7, 2006: 603.5, 2007: 695.4, 2008: 871.7, 2009: 972.4,
    2010: 1224.5,2011: 1571.5,2012: 1668.9,2013: 1411.2,2014: 1266.4,
    2015: 1160.1,2016: 1250.8,2017: 1257.0,2018: 1268.5,2019: 1393.4,
    2020: 1769.6,2021: 1798.6,2022: 1800.9,2023: 1941.0,2024: 2300.0,
    2025: 3380.0,
}

SILVER_PRICES = {
    1970: 1.6,  1971: 1.5,  1972: 1.7,  1973: 2.6,  1974: 4.7,
    1975: 4.4,  1976: 4.4,  1977: 4.6,  1978: 5.4,  1979: 11.1,
    1980: 20.6, 1981: 10.5, 1982: 7.9,  1983: 11.4, 1984: 8.1,
    1985: 6.1,  1986: 5.5,  1987: 7.0,  1988: 6.5,  1989: 5.5,
    1990: 4.8,  1991: 4.1,  1992: 3.9,  1993: 4.3,  1994: 5.3,
    1995: 5.2,  1996: 5.2,  1997: 4.9,  1998: 5.5,  1999: 5.2,
    2000: 4.9,  2001: 4.4,  2002: 4.6,  2003: 4.9,  2004: 6.7,
    2005: 7.3,  2006: 11.5, 2007: 13.4, 2008: 14.9, 2009: 14.7,
    2010: 20.2, 2011: 35.1, 2012: 31.2, 2013: 23.8, 2014: 19.1,
    2015: 15.7, 2016: 17.1, 2017: 17.0, 2018: 15.7, 2019: 16.2,
    2020: 20.5, 2021: 25.1, 2022: 21.8, 2023: 23.4, 2024: 28.5,
    2025: 33.0,
}

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("## 📉 Macro Trends")
st.caption("Long-run economic narratives: USD purchasing power erosion and precious metals history")
st.divider()

tab1, tab2 = st.tabs(["💵 USD Purchasing Power", "🥇 Gold vs Silver"])

# ── Tab 1: USD Purchasing Power ───────────────────────────────────────────
with tab1:
    st.markdown("#### US Dollar Purchasing Power Erosion (1970 – 2024)")
    st.caption("How much a 1970 dollar is worth each year, adjusted for cumulative CPI inflation")

    base_year = st.slider("Base Year", 1970, 2010, 1970, step=5)

    # Build series from base year forward
    years = sorted(k for k in US_INFLATION if k >= base_year)
    pp = 100.0
    purchasing_power = [100.0]
    inflation_rates = [US_INFLATION.get(y, 0) for y in years[1:]]
    for rate in inflation_rates:
        pp = pp / (1 + rate / 100)
        purchasing_power.append(round(pp, 2))

    pp_df = pd.DataFrame({"year": years, "purchasing_power": purchasing_power,
                           "inflation": [US_INFLATION.get(y, 0) for y in years]})

    # Dual-axis: inflation bars + PP line
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Inflation bars
    bar_colors = ["#d32f2f" if r > 5 else "#f57c00" if r > 3 else "#388e3c" if r >= 0 else "#00D4FF"
                  for r in pp_df["inflation"]]
    fig.add_trace(
        go.Bar(
            x=pp_df["year"], y=pp_df["inflation"],
            name="Annual Inflation (%)",
            marker_color=bar_colors,
            opacity=0.6,
            hovertemplate="<b>%{x}</b><br>Inflation: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=False,
    )

    # Purchasing power line
    fig.add_trace(
        go.Scatter(
            x=pp_df["year"], y=pp_df["purchasing_power"],
            name=f"Purchasing Power (${base_year}=100)",
            line=dict(color="#00D4FF", width=3),
            fill="tozeroy",
            fillcolor="rgba(0,212,255,0.07)",
            hovertemplate="<b>%{x}</b><br>Purchasing Power: $%{y:.1f}<extra></extra>",
            mode="lines",
        ),
        secondary_y=True,
    )

    final_pp = purchasing_power[-1]
    fig.update_layout(
        height=480,
        title=dict(text=f"USD Purchasing Power · ${base_year}=100 → ${final_pp:.1f} by {years[-1]}", font=dict(size=15)),
        margin=dict(l=60, r=60, t=60, b=40),
        hovermode="x unified",
        template="streamlit",
    )
    fig.update_yaxes(title_text="Annual Inflation (%)", secondary_y=False)
    fig.update_yaxes(title_text=f"Purchasing Power (${base_year}=100)", secondary_y=True)

    st.plotly_chart(fig, use_container_width=True)

    # Key metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"${base_year} is worth today", f"${final_pp:.1f}c" if final_pp < 10 else f"${final_pp:.1f}")
    c2.metric("Cumulative erosion", f"{100 - final_pp:.1f}%")
    peak_infl_year = max(US_INFLATION, key=US_INFLATION.get)
    c3.metric("Peak inflation year", str(peak_infl_year), f"{US_INFLATION[peak_infl_year]:.1f}%")
    avg_infl = sum(US_INFLATION[y] for y in years) / len(years)
    c4.metric("Avg annual inflation", f"{avg_infl:.2f}%", f"over {len(years)} years")

    st.divider()
    st.caption(
        "**Source:** US Bureau of Labor Statistics (CPI). "
        "Purchasing power = cumulative compounding of inverse CPI. "
        "Green bars = inflation ≤ 3%, orange = 3–5%, red = >5%, blue = deflation."
    )

# ── Tab 2: Gold vs Silver ─────────────────────────────────────────────────
with tab2:
    st.markdown("#### Gold vs Silver Prices (1970 – 2025)")
    st.caption("Dual-axis precious metals comparison with gold/silver ratio overlay")

    years_pm = sorted(GOLD_PRICES.keys())
    gold_vals = [GOLD_PRICES[y] for y in years_pm]
    silver_vals = [SILVER_PRICES.get(y) for y in years_pm]
    gs_ratio = [g / s if s else None for g, s in zip(gold_vals, silver_vals)]

    show_ratio = st.toggle("Show Gold/Silver Ratio", value=True)

    fig2 = make_subplots(specs=[[{"secondary_y": True}]])

    # Gold area
    fig2.add_trace(
        go.Scatter(
            x=years_pm, y=gold_vals,
            name="Gold (USD/oz)",
            line=dict(color="#FFE66D", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(255,230,109,0.08)",
            hovertemplate="<b>%{x}</b><br>Gold: $%{y:,.0f}/oz<extra></extra>",
            mode="lines",
        ),
        secondary_y=False,
    )

    # Silver line
    fig2.add_trace(
        go.Scatter(
            x=years_pm, y=silver_vals,
            name="Silver (USD/oz)",
            line=dict(color="#C0C0C0", width=2, dash="dash"),
            hovertemplate="<b>%{x}</b><br>Silver: $%{y:.2f}/oz<extra></extra>",
            mode="lines",
        ),
        secondary_y=False,
    )

    if show_ratio:
        fig2.add_trace(
            go.Scatter(
                x=years_pm, y=gs_ratio,
                name="Gold/Silver Ratio",
                line=dict(color="#FF6B6B", width=1.5, dash="dot"),
                hovertemplate="<b>%{x}</b><br>G/S Ratio: %{y:.1f}x<extra></extra>",
                mode="lines",
            ),
            secondary_y=True,
        )

    # Notable events
    events = {1980: "Hunt Brothers squeeze", 2008: "Financial crisis", 2011: "All-time high (then)", 2020: "COVID rally", 2025: "New ATH $3,380"}
    for yr, label in events.items():
        if yr in GOLD_PRICES:
            fig2.add_vline(
                x=yr, line_dash="dot", line_color="rgba(255,255,255,0.15)",
                annotation_text=label, annotation_font_color="#64748B",
                annotation_font_size=10, annotation_position="top left",
            )

    fig2.update_layout(
        height=500,
        title=dict(text="Gold vs Silver Price History (USD/oz)", font=dict(size=15)),
        margin=dict(l=60, r=60, t=60, b=40),
        hovermode="x unified",
        template="streamlit",
    )
    fig2.update_yaxes(title_text="Price (USD/oz)", secondary_y=False)
    if show_ratio:
        fig2.update_yaxes(title_text="Gold/Silver Ratio (×)", secondary_y=True)

    st.plotly_chart(fig2, use_container_width=True)

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gold (2025)", f"${GOLD_PRICES[2025]:,.0f}/oz", f"+{((GOLD_PRICES[2025]/GOLD_PRICES[1970])-1)*100:.0f}% since 1970")
    c2.metric("Silver (2025)", f"${SILVER_PRICES[2025]:.2f}/oz", f"+{((SILVER_PRICES[2025]/SILVER_PRICES[1970])-1)*100:.0f}% since 1970")
    latest_ratio = GOLD_PRICES[2025] / SILVER_PRICES[2025]
    hist_avg_ratio = sum(GOLD_PRICES[y] / SILVER_PRICES[y] for y in years_pm if y in SILVER_PRICES) / len(years_pm)
    c3.metric("Current G/S Ratio", f"{latest_ratio:.1f}×", f"Historical avg: {hist_avg_ratio:.1f}×")
    gold_peak = max(GOLD_PRICES, key=GOLD_PRICES.get)
    c4.metric("Gold Peak Year", str(gold_peak), f"${GOLD_PRICES[gold_peak]:,.0f}/oz")

    st.divider()
    st.caption(
        "**Source:** FRED (GOLDAMGBD228NLBM, SLVPRUSD) / hardcoded fallback. "
        "Gold/Silver ratio above ~80× historically signals silver is undervalued relative to gold. "
        "2025 price reflects spot as of June 2025."
    )
