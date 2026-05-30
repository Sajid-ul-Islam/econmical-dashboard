"""
Data fetching layer.
Sources:
  - World Bank API (no key needed) — GDP, GDP per capita, debt
  - FRED API (free key) — gold price
  - All results stored/cached in Supabase
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from utils.database import (
    upsert_economic_data,
    update_freshness,
    get_freshness,
    fetch_economic_data,
)

# World Bank indicator codes
WB_INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD",           # GDP (current USD)
    "gdp_per_capita": "NY.GDP.PCAP.CD", # GDP per capita (current USD)
    "debt_pct_gdp": "GC.DOD.TOTL.GD.ZS", # Central gov debt (% of GDP)
}

GOLD_INDICATOR = "gold_price"
STALE_HOURS = 24  # Refresh if older than this


def is_stale(country_code: str, indicator: str) -> bool:
    """Check if data needs refresh."""
    fresh = get_freshness(country_code, indicator)
    if not fresh:
        return True
    last = fresh.get("last_fetched")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - last_dt) > timedelta(hours=STALE_HOURS)
    except Exception:
        return True


@st.cache_data(ttl=3600)
def fetch_world_bank(indicator_code: str, country_code: str, year_start=1990, year_end=2023):
    """Fetch from World Bank API."""
    url = (
        f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}"
        f"?format=json&per_page=100&mrv=40&date={year_start}:{year_end}"
    )
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        if len(data) < 2 or not data[1]:
            return []
        rows = []
        for item in data[1]:
            if item.get("value") is not None:
                rows.append({
                    "year": int(item["date"]),
                    "value": float(item["value"]),
                    "country_name": item["country"]["value"],
                })
        return rows
    except Exception as e:
        return []


@st.cache_data(ttl=3600)
def fetch_gold_price_fred(year_start=1990, year_end=2023) -> list[dict]:
    """Fetch annual gold price from FRED (GOLDAMGBD228NLBM)."""
    try:
        api_key = st.secrets.get("fred", {}).get("api_key", "")
        if not api_key:
            return _fallback_gold_data()

        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=GOLDAMGBD228NLBM&api_key={api_key}"
            f"&file_type=json&observation_start={year_start}-01-01"
            f"&observation_end={year_end}-12-31&frequency=a"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        rows = []
        for obs in data.get("observations", []):
            if obs["value"] != ".":
                rows.append({
                    "year": int(obs["date"][:4]),
                    "value": float(obs["value"]),
                    "country_name": "World",
                })
        return rows
    except Exception:
        return _fallback_gold_data()


def _fallback_gold_data() -> list[dict]:
    """Historical gold prices USD/oz — hardcoded fallback."""
    data = {
        1990: 383.5, 1991: 362.1, 1992: 344.7, 1993: 359.8, 1994: 384.0,
        1995: 384.1, 1996: 387.7, 1997: 331.0, 1998: 294.2, 1999: 278.9,
        2000: 279.1, 2001: 271.0, 2002: 309.7, 2003: 363.4, 2004: 409.2,
        2005: 444.7, 2006: 603.5, 2007: 695.4, 2008: 871.7, 2009: 972.4,
        2010: 1224.5, 2011: 1571.5, 2012: 1668.9, 2013: 1411.2, 2014: 1266.4,
        2015: 1160.1, 2016: 1250.8, 2017: 1257.0, 2018: 1268.5, 2019: 1393.4,
        2020: 1769.6, 2021: 1798.6, 2022: 1800.9, 2023: 1941.0, 2024: 2300.0,
    }
    return [{"year": y, "value": v, "country_name": "World"} for y, v in data.items()]


@st.cache_data(ttl=3600)
def get_all_countries() -> list[dict]:
    """Fetch full country list from World Bank."""
    try:
        url = "https://api.worldbank.org/v2/country?format=json&per_page=300"
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        countries = []
        for c in data[1]:
            if c.get("region", {}).get("id") not in ["NA", ""] and c.get("capitalCity"):
                countries.append({
                    "code": c["id"],
                    "name": c["name"],
                    "region": c.get("region", {}).get("value", ""),
                    "income_level": c.get("incomeLevel", {}).get("value", ""),
                })
        return sorted(countries, key=lambda x: x["name"])
    except Exception:
        return _fallback_countries()


def _fallback_countries():
    return [
        {"code": "USA", "name": "United States", "region": "North America", "income_level": "High income"},
        {"code": "CHN", "name": "China", "region": "East Asia & Pacific", "income_level": "Upper middle income"},
        {"code": "DEU", "name": "Germany", "region": "Europe & Central Asia", "income_level": "High income"},
        {"code": "JPN", "name": "Japan", "region": "East Asia & Pacific", "income_level": "High income"},
        {"code": "GBR", "name": "United Kingdom", "region": "Europe & Central Asia", "income_level": "High income"},
        {"code": "FRA", "name": "France", "region": "Europe & Central Asia", "income_level": "High income"},
        {"code": "IND", "name": "India", "region": "South Asia", "income_level": "Lower middle income"},
        {"code": "BRA", "name": "Brazil", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
        {"code": "BGD", "name": "Bangladesh", "region": "South Asia", "income_level": "Lower middle income"},
        {"code": "PAK", "name": "Pakistan", "region": "South Asia", "income_level": "Lower middle income"},
        {"code": "IDN", "name": "Indonesia", "region": "East Asia & Pacific", "income_level": "Upper middle income"},
        {"code": "NGA", "name": "Nigeria", "region": "Sub-Saharan Africa", "income_level": "Lower middle income"},
        {"code": "ZAF", "name": "South Africa", "region": "Sub-Saharan Africa", "income_level": "Upper middle income"},
        {"code": "TUR", "name": "Turkey", "region": "Europe & Central Asia", "income_level": "Upper middle income"},
        {"code": "SAU", "name": "Saudi Arabia", "region": "Middle East & North Africa", "income_level": "High income"},
        {"code": "ARG", "name": "Argentina", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
        {"code": "MEX", "name": "Mexico", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
        {"code": "KOR", "name": "South Korea", "region": "East Asia & Pacific", "income_level": "High income"},
        {"code": "CAN", "name": "Canada", "region": "North America", "income_level": "High income"},
        {"code": "AUS", "name": "Australia", "region": "East Asia & Pacific", "income_level": "High income"},
        {"code": "RUS", "name": "Russia", "region": "Europe & Central Asia", "income_level": "Upper middle income"},
        {"code": "EGY", "name": "Egypt", "region": "Middle East & North Africa", "income_level": "Lower middle income"},
    ]


def load_country_data(country_code: str, country_name: str, force: bool = False) -> bool:
    """
    Load all indicators for a country into Supabase.
    Skips if data is fresh (unless force=True).
    Returns True if data was fetched/updated.
    """
    fetched_any = False

    for indicator, wb_code in WB_INDICATORS.items():
        if not force and not is_stale(country_code, indicator):
            continue

        rows_raw = fetch_world_bank(wb_code, country_code)
        if rows_raw:
            rows = [
                {
                    "country_code": country_code,
                    "country_name": country_name,
                    "indicator": indicator,
                    "year": r["year"],
                    "value": r["value"],
                    "source": "World Bank API",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                for r in rows_raw
            ]
            upsert_economic_data(rows)
            update_freshness(country_code, indicator, "ok")
            fetched_any = True

    # Gold price — same for all countries, stored under "WLD"
    if not force and not is_stale("WLD", GOLD_INDICATOR):
        pass
    else:
        gold_rows = fetch_gold_price_fred()
        if gold_rows:
            rows = [
                {
                    "country_code": "WLD",
                    "country_name": "World",
                    "indicator": GOLD_INDICATOR,
                    "year": r["year"],
                    "value": r["value"],
                    "source": "FRED / Fallback",
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                for r in gold_rows
            ]
            upsert_economic_data(rows)
            update_freshness("WLD", GOLD_INDICATOR, "ok")
            fetched_any = True

    return fetched_any


def get_country_data_cached(
    country_codes: list[str],
    indicators: list[str],
    year_start: int,
    year_end: int,
) -> pd.DataFrame:
    """
    Returns data from Supabase. Auto-fetches if stale.
    """
    countries = get_all_countries()
    country_map = {c["code"]: c["name"] for c in countries}

    for code in country_codes:
        name = country_map.get(code, code)
        # Quietly refresh in background if stale
        for ind in indicators:
            if ind != GOLD_INDICATOR and is_stale(code, ind):
                load_country_data(code, name)
                break

    df = fetch_economic_data(country_codes, indicators, year_start, year_end)

    # Also fetch gold if requested
    if GOLD_INDICATOR in indicators:
        gold_df = fetch_economic_data(["WLD"], [GOLD_INDICATOR], year_start, year_end)
        if not gold_df.empty:
            df = pd.concat([df, gold_df], ignore_index=True)

    return df
