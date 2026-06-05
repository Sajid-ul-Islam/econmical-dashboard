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
import os
from datetime import datetime, timezone, timedelta
from utils.database import (
    upsert_economic_data,
    update_freshness,
    batch_update_freshness,
    get_freshness,
    fetch_economic_data,
)

# World Bank indicator codes
WB_INDICATORS = {
    "gdp": "NY.GDP.MKTP.CD",           # GDP (current USD)
    "gdp_per_capita": "NY.GDP.PCAP.CD", # GDP per capita (current USD)
    "debt_pct_gdp": "GC.DOD.TOTL.GD.ZS", # Central gov debt (% of GDP)
    "inflation": "FP.CPI.TOTL.ZG",      # Inflation, consumer prices (annual %)
    "unemployment": "SL.UEM.TOTL.ZS",   # Unemployment, total (% of total labor force)
    "life_expectancy": "SP.DYN.LE00.IN", # Life expectancy at birth, total (years)
}

GOLD_INDICATOR = "gold_price"
SILVER_INDICATOR = "silver_price"
OIL_INDICATOR = "oil_price"
DXY_INDICATOR = "dxy"
STALE_HOURS = 24  # Refresh if older than this

# Path to static debt snapshot CSV
_HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DEBT_CSV = os.path.join(_HERE, "../data/global_debt_2024.csv")


def get_last_updated_str(df_sub: pd.DataFrame) -> str:
    """Helper to extract and format the latest fetched_at timestamp."""
    if "fetched_at" in df_sub.columns and not df_sub.empty:
        val = df_sub["fetched_at"].dropna().max()
        if pd.notna(val):
            try:
                return pd.to_datetime(val).strftime('%Y-%m-%d %H:%M UTC')
            except Exception:
                pass
    return "Calculated Proxy / Unknown"


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


def get_global_debt_snapshot() -> pd.DataFrame:
    """Returns 173-country debt snapshot from static CSV — instant, no API needed."""
    try:
        df = pd.read_csv(STATIC_DEBT_CSV)
        df["year"] = 2024
        df["indicator"] = "debt_pct_gdp"
        df["source"] = "Static snapshot (IMF/WB 2024)"
        df["fetched_at"] = datetime.now(timezone.utc).isoformat()
        return df[["country_code", "country_name", "indicator", "year", "value", "source", "fetched_at"]]
    except Exception:
        return pd.DataFrame()


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


def _fallback_silver_data() -> list[dict]:
    """Historical silver prices USD/oz — hardcoded fallback."""
    data = {
        1990: 4.8, 1991: 4.1, 1992: 3.9, 1993: 4.3, 1994: 5.3,
        1995: 5.2, 1996: 5.2, 1997: 4.9, 1998: 5.5, 1999: 5.2,
        2000: 4.9, 2001: 4.4, 2002: 4.6, 2003: 4.9, 2004: 6.7,
        2005: 7.3, 2006: 11.5, 2007: 13.4, 2008: 14.9, 2009: 14.7,
        2010: 20.2, 2011: 35.1, 2012: 31.2, 2013: 23.8, 2014: 19.1,
        2015: 15.7, 2016: 17.1, 2017: 17.0, 2018: 15.7, 2019: 16.2,
        2020: 20.5, 2021: 25.1, 2022: 21.8, 2023: 23.4, 2024: 28.5,
    }
    return [{"year": y, "value": v, "country_name": "World"} for y, v in data.items()]


@st.cache_data(ttl=3600)
def fetch_silver_price_fred(year_start=1990, year_end=2024) -> list[dict]:
    """Fetch annual silver price from FRED (SLVPRUSD)."""
    try:
        api_key = st.secrets.get("fred", {}).get("api_key", "")
        if not api_key:
            return _fallback_silver_data()
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=SLVPRUSD&api_key={api_key}"
            f"&file_type=json&observation_start={year_start}-01-01"
            f"&observation_end={year_end}-12-31&frequency=a"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        rows = []
        for obs in data.get("observations", []):
            if obs["value"] != ".":
                rows.append({"year": int(obs["date"][:4]), "value": float(obs["value"]), "country_name": "World"})
        return rows if rows else _fallback_silver_data()
    except Exception:
        return _fallback_silver_data()


@st.cache_data(ttl=3600)
def fetch_oil_price_fred(year_start=1990, year_end=2023) -> list[dict]:
    """Fetch annual Brent crude oil price from FRED (POILBREUSDM)."""
    try:
        api_key = st.secrets.get("fred", {}).get("api_key", "")
        if not api_key:
            return _fallback_oil_data()

        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=POILBREUSDM&api_key={api_key}"
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
        return _fallback_oil_data()


def _fallback_oil_data() -> list[dict]:
    """Historical Brent Crude prices USD/bbl — hardcoded fallback."""
    data = {
        1990: 23.73, 1991: 20.00, 1992: 19.32, 1993: 16.97, 1994: 15.82,
        1995: 17.02, 1996: 20.67, 1997: 19.09, 1998: 12.72, 1999: 17.97,
        2000: 28.50, 2001: 24.44, 2002: 25.02, 2003: 28.83, 2004: 38.27,
        2005: 54.19, 2006: 65.14, 2007: 72.39, 2008: 97.26, 2009: 61.67,
        2010: 79.50, 2011: 111.26, 2012: 111.67, 2013: 108.66, 2014: 98.95,
        2015: 52.39, 2016: 43.73, 2017: 54.19, 2018: 71.31, 2019: 64.22,
        2020: 41.84, 2021: 70.89, 2022: 100.93, 2023: 82.49, 2024: 83.00,
    }
    return [{"year": y, "value": v, "country_name": "World"} for y, v in data.items()]


@st.cache_data(ttl=3600)
def fetch_dxy_fred(year_start=1990, year_end=2023) -> list[dict]:
    """Fetch annual US Dollar Index from FRED (DTWEXBGS)."""
    try:
        api_key = st.secrets.get("fred", {}).get("api_key", "")
        if not api_key:
            return _fallback_dxy_data()

        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=DTWEXBGS&api_key={api_key}"
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
        return _fallback_dxy_data()


def _fallback_dxy_data() -> list[dict]:
    """Historical US Dollar Index (DXY) — hardcoded fallback."""
    data = {
        1990: 92.0, 1991: 91.0, 1992: 89.0, 1993: 92.0, 1994: 91.0,
        1995: 86.0, 1996: 88.0, 1997: 94.0, 1998: 100.0, 1999: 102.0,
        2000: 108.0, 2001: 113.0, 2002: 114.0, 2003: 103.0, 2004: 94.0,
        2005: 89.0, 2006: 88.0, 2007: 83.0, 2008: 77.0, 2009: 81.0,
        2010: 80.0, 2011: 76.0, 2012: 80.0, 2013: 81.0, 2014: 83.0,
        2015: 93.0, 2016: 98.0, 2017: 99.0, 2018: 94.0, 2019: 97.0,
        2020: 96.0, 2021: 93.0, 2022: 104.0, 2023: 103.0, 2024: 104.5,
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
                    "iso2": c.get("iso2Code", ""),
                    "name": c["name"],
                    "region": c.get("region", {}).get("value", ""),
                    "income_level": c.get("incomeLevel", {}).get("value", ""),
                })
        return sorted(countries, key=lambda x: x["name"])
    except Exception:
        return _fallback_countries()


def _fallback_countries():
    return [
        {"code": "USA", "iso2": "US", "name": "United States", "region": "North America", "income_level": "High income"},
        {"code": "CHN", "iso2": "CN", "name": "China", "region": "East Asia & Pacific", "income_level": "Upper middle income"},
        {"code": "DEU", "iso2": "DE", "name": "Germany", "region": "Europe & Central Asia", "income_level": "High income"},
        {"code": "JPN", "iso2": "JP", "name": "Japan", "region": "East Asia & Pacific", "income_level": "High income"},
        {"code": "GBR", "iso2": "GB", "name": "United Kingdom", "region": "Europe & Central Asia", "income_level": "High income"},
        {"code": "FRA", "iso2": "FR", "name": "France", "region": "Europe & Central Asia", "income_level": "High income"},
        {"code": "IND", "iso2": "IN", "name": "India", "region": "South Asia", "income_level": "Lower middle income"},
        {"code": "BRA", "iso2": "BR", "name": "Brazil", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
        {"code": "BGD", "iso2": "BD", "name": "Bangladesh", "region": "South Asia", "income_level": "Lower middle income"},
        {"code": "PAK", "iso2": "PK", "name": "Pakistan", "region": "South Asia", "income_level": "Lower middle income"},
        {"code": "IDN", "iso2": "ID", "name": "Indonesia", "region": "East Asia & Pacific", "income_level": "Upper middle income"},
        {"code": "NGA", "iso2": "NG", "name": "Nigeria", "region": "Sub-Saharan Africa", "income_level": "Lower middle income"},
        {"code": "ZAF", "iso2": "ZA", "name": "South Africa", "region": "Sub-Saharan Africa", "income_level": "Upper middle income"},
        {"code": "TUR", "iso2": "TR", "name": "Turkey", "region": "Europe & Central Asia", "income_level": "Upper middle income"},
        {"code": "SAU", "iso2": "SA", "name": "Saudi Arabia", "region": "Middle East & North Africa", "income_level": "High income"},
        {"code": "ARG", "iso2": "AR", "name": "Argentina", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
        {"code": "MEX", "iso2": "MX", "name": "Mexico", "region": "Latin America & Caribbean", "income_level": "Upper middle income"},
        {"code": "KOR", "iso2": "KR", "name": "South Korea", "region": "East Asia & Pacific", "income_level": "High income"},
        {"code": "CAN", "iso2": "CA", "name": "Canada", "region": "North America", "income_level": "High income"},
        {"code": "AUS", "iso2": "AU", "name": "Australia", "region": "East Asia & Pacific", "income_level": "High income"},
        {"code": "RUS", "iso2": "RU", "name": "Russia", "region": "Europe & Central Asia", "income_level": "Upper middle income"},
        {"code": "EGY", "iso2": "EG", "name": "Egypt", "region": "Middle East & North Africa", "income_level": "Lower middle income"},
    ]


def load_country_data(country_code: str, country_name: str, force: bool = False) -> bool:
    """
    Load all indicators for a country into Supabase.
    Skips if data is fresh (unless force=True).
    Returns True if data was fetched/updated.
    """
    fetched_any = False
    all_data_rows = []
    freshness_updates = []
    now_str = datetime.now(timezone.utc).isoformat()

    for indicator, wb_code in WB_INDICATORS.items():
        if not force and not is_stale(country_code, indicator):
            continue

        rows_raw = fetch_world_bank(wb_code, country_code)
        if rows_raw:
            all_data_rows.extend([
                {
                    "country_code": country_code,
                    "country_name": country_name,
                    "indicator": indicator,
                    "year": r["year"],
                    "value": r["value"],
                    "source": "World Bank API",
                    "fetched_at": now_str,
                }
                for r in rows_raw
            ])
            freshness_updates.append({"country_code": country_code, "indicator": indicator, "last_fetched": now_str, "status": "ok"})
            fetched_any = True

    # Gold price — same for all countries, stored under "WLD"
    if force or is_stale("WLD", GOLD_INDICATOR):
        gold_rows = fetch_gold_price_fred()
        if gold_rows:
            all_data_rows.extend([
                {
                    "country_code": "WLD",
                    "country_name": "World",
                    "indicator": GOLD_INDICATOR,
                    "year": r["year"],
                    "value": r["value"],
                    "source": "FRED / Fallback",
                    "fetched_at": now_str,
                }
                for r in gold_rows
            ])
            freshness_updates.append({"country_code": "WLD", "indicator": GOLD_INDICATOR, "last_fetched": now_str, "status": "ok"})
            fetched_any = True

    # Silver price
    if force or is_stale("WLD", SILVER_INDICATOR):
        silver_rows = fetch_silver_price_fred()
        if silver_rows:
            all_data_rows.extend([
                {
                    "country_code": "WLD",
                    "country_name": "World",
                    "indicator": SILVER_INDICATOR,
                    "year": r["year"],
                    "value": r["value"],
                    "source": "FRED / Fallback",
                    "fetched_at": now_str,
                }
                for r in silver_rows
            ])
            freshness_updates.append({"country_code": "WLD", "indicator": SILVER_INDICATOR, "last_fetched": now_str, "status": "ok"})
            fetched_any = True

    # Oil price
    if force or is_stale("WLD", OIL_INDICATOR):
        oil_rows = fetch_oil_price_fred()
        if oil_rows:
            all_data_rows.extend([
                {
                    "country_code": "WLD",
                    "country_name": "World",
                    "indicator": OIL_INDICATOR,
                    "year": r["year"],
                    "value": r["value"],
                    "source": "FRED / Fallback",
                    "fetched_at": now_str,
                }
                for r in oil_rows
            ])
            freshness_updates.append({"country_code": "WLD", "indicator": OIL_INDICATOR, "last_fetched": now_str, "status": "ok"})
            fetched_any = True

    # DXY Index
    if force or is_stale("WLD", DXY_INDICATOR):
        dxy_rows = fetch_dxy_fred()
        if dxy_rows:
            all_data_rows.extend([
                {
                    "country_code": "WLD",
                    "country_name": "World",
                    "indicator": DXY_INDICATOR,
                    "year": r["year"],
                    "value": r["value"],
                    "source": "FRED / Fallback",
                    "fetched_at": now_str,
                }
                for r in dxy_rows
            ])
            freshness_updates.append({"country_code": "WLD", "indicator": DXY_INDICATOR, "last_fetched": now_str, "status": "ok"})
            fetched_any = True

    if all_data_rows:
        upsert_economic_data(all_data_rows)
        
    if freshness_updates:
        batch_update_freshness(freshness_updates)

    return fetched_any


@st.cache_data(ttl=3600, show_spinner=False)
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

    # Check global/world indicators
    global_inds = [GOLD_INDICATOR, SILVER_INDICATOR, OIL_INDICATOR, DXY_INDICATOR]
    if any(i in indicators for i in global_inds):
        for gi in global_inds:
            if gi in indicators and is_stale("WLD", gi):
                load_country_data("WLD", "World")
                break

    for code in country_codes:
        name = country_map.get(code, code)
        # Quietly refresh in background if stale
        for ind in indicators:
            if ind not in global_inds and is_stale(code, ind):
                load_country_data(code, name)
                break

    df = fetch_economic_data(country_codes, indicators, year_start, year_end)

    # Also fetch gold if requested
    if GOLD_INDICATOR in indicators:
        gold_df = fetch_economic_data(["WLD"], [GOLD_INDICATOR], year_start, year_end)
        if not gold_df.empty:
            df = pd.concat([df, gold_df], ignore_index=True)

    # Also fetch silver if requested
    if SILVER_INDICATOR in indicators:
        silver_df = fetch_economic_data(["WLD"], [SILVER_INDICATOR], year_start, year_end)
        if not silver_df.empty:
            df = pd.concat([df, silver_df], ignore_index=True)

    # Also fetch oil if requested
    if OIL_INDICATOR in indicators:
        oil_df = fetch_economic_data(["WLD"], [OIL_INDICATOR], year_start, year_end)
        if not oil_df.empty:
            df = pd.concat([df, oil_df], ignore_index=True)

    # Also fetch DXY if requested
    if DXY_INDICATOR in indicators:
        dxy_df = fetch_economic_data(["WLD"], [DXY_INDICATOR], year_start, year_end)
        if not dxy_df.empty:
            df = pd.concat([df, dxy_df], ignore_index=True)

    return df
