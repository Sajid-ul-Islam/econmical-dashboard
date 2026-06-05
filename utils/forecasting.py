"""
Forecasting layer using Prophet.
Generates 5-year predictions with confidence intervals.
Stores results in Supabase predictions table.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from utils.database import upsert_predictions, fetch_predictions


@st.cache_data(ttl=86400, show_spinner=False) # Cache for 24 hours
def run_prophet_forecast(
    df: pd.DataFrame,
    country_code: str,
    indicator: str,
    forecast_years: int = 7,
) -> pd.DataFrame | None:
    """
    Fit Prophet on historical data and return predictions df.
    df must have columns: year, value
    """
    try:
        from prophet import Prophet
        import logging
        logging.getLogger("prophet").setLevel(logging.ERROR)
        logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
    except ImportError:
        if "prophet_warning_shown" not in st.session_state:
            st.warning("⚠️ Prophet library is missing! Falling back to simple linear trend forecasting.", icon="⚠️")
            st.session_state.prophet_warning_shown = True
        return _fallback_forecast(df, country_code, indicator, forecast_years)

    series = df[["year", "value"]].dropna().copy()
    if len(series) < 5:
        return None

    series["ds"] = pd.to_datetime(series["year"].astype(str) + "-06-01")
    series = series.rename(columns={"value": "y"})

    try:
        m = Prophet(
            yearly_seasonality=False,
            weekly_seasonality=False,
            daily_seasonality=False,
            interval_width=0.80,
            changepoint_prior_scale=0.3,
        )
        m.fit(series[["ds", "y"]])

        last_year = int(df["year"].max())
        future_years = list(range(last_year + 1, last_year + forecast_years + 1))
        future_df = pd.DataFrame({
            "ds": pd.to_datetime([f"{y}-06-01" for y in future_years])
        })

        forecast = m.predict(future_df)
        result = pd.DataFrame({
            "country_code": country_code,
            "indicator": indicator,
            "year": future_years,
            "predicted": forecast["yhat"].values,
            "lower_bound": forecast["yhat_lower"].values,
            "upper_bound": forecast["yhat_upper"].values,
            "model": "prophet",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return result
    except Exception as e:
        return _fallback_forecast(df, country_code, indicator, forecast_years)


def _fallback_forecast(
    df: pd.DataFrame,
    country_code: str,
    indicator: str,
    forecast_years: int = 7,
) -> pd.DataFrame | None:
    """Simple linear trend fallback if Prophet fails."""
    series = df[["year", "value"]].dropna().copy()
    if len(series) < 3:
        return None

    x = series["year"].values
    y = series["value"].values
    coeffs = np.polyfit(x, y, 1)
    trend = np.poly1d(coeffs)

    residuals = y - trend(x)
    std = residuals.std()

    last_year = int(df["year"].max())
    future_years = list(range(last_year + 1, last_year + forecast_years + 1))
    predicted = trend(np.array(future_years))

    result = pd.DataFrame({
        "country_code": country_code,
        "indicator": indicator,
        "year": future_years,
        "predicted": predicted,
        "lower_bound": predicted - 1.5 * std,
        "upper_bound": predicted + 1.5 * std,
        "model": "linear_trend",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return result


def get_or_create_forecast(
    df: pd.DataFrame,
    country_code: str,
    indicator: str,
    force_recompute: bool = False,
) -> pd.DataFrame:
    """
    Returns forecast from DB if exists, else computes + stores it.
    """
    if not force_recompute:
        cached = fetch_predictions([country_code], [indicator])
        if not cached.empty:
            return cached

    forecast = run_prophet_forecast(df, country_code, indicator)
    if forecast is not None and not forecast.empty:
        rows = forecast.to_dict("records")
        upsert_predictions(rows)
        return forecast

    return pd.DataFrame()


def get_or_create_forecasts_batch(
    df: pd.DataFrame,
    country_codes: list[str],
    indicators: list[str],
    force_recompute: bool = False,
) -> pd.DataFrame:
    """
    Batch fetches forecasts from DB, and only computes missing ones.
    Drastically reduces database roundtrips.
    """
    all_preds = []
    new_rows = []

    if not force_recompute:
        cached = fetch_predictions(country_codes, indicators)
        if not cached.empty:
            all_preds.append(cached)

    cached_pairs = set()
    if all_preds and not all_preds[0].empty:
        cached_pairs = set(zip(all_preds[0]["country_code"], all_preds[0]["indicator"]))

    for code in country_codes:
        for indicator in indicators:
            if not force_recompute and (code, indicator) in cached_pairs:
                continue
            cdf = df[(df["country_code"] == code) & (df["indicator"] == indicator)]
            if cdf.empty:
                continue
            forecast = run_prophet_forecast(cdf, code, indicator)
            if forecast is not None and not forecast.empty:
                all_preds.append(forecast)
                new_rows.extend(forecast.to_dict("records"))

    if new_rows:
        upsert_predictions(new_rows)

    if all_preds:
        return pd.concat(all_preds, ignore_index=True)
    return pd.DataFrame()


def detect_anomalies(df: pd.DataFrame, z_threshold: float = 2.5) -> pd.DataFrame:
    """
    Flag anomalous data points using z-score on YoY growth rate.
    Returns df with added 'anomaly' and 'yoy_growth' columns.
    """
    df = df.copy().sort_values("year")
    df["yoy_growth"] = df["value"].pct_change() * 100
    mean = df["yoy_growth"].mean()
    std = df["yoy_growth"].std()
    if std > 0:
        df["z_score"] = (df["yoy_growth"] - mean) / std
        df["anomaly"] = df["z_score"].abs() > z_threshold
    else:
        df["z_score"] = 0.0
        df["anomaly"] = False
    return df


def compute_economic_health_score(country_df: pd.DataFrame, latest_year: int) -> dict:
    """
    Composite economic health score (0-100) from latest year data.
    Weights: GDP per capita (30%), debt ratio (25%, inverted),
             inflation (25%, inverted), unemployment (20%, inverted)
    """
    scores = {}
    latest = country_df[country_df["year"] == latest_year]

    def safe_get(indicator):
        row = latest[latest["indicator"] == indicator]
        return float(row["value"].iloc[0]) if not row.empty else None

    gdp_pc = safe_get("gdp_per_capita")
    debt = safe_get("debt_pct_gdp")
    inflation = safe_get("inflation")
    unemployment = safe_get("unemployment")

    # Normalize per capita GDP (log scale, 0-100)
    if gdp_pc:
        import math
        pc_score = min(100, max(0, (math.log(max(gdp_pc, 500)) - math.log(500)) / (math.log(80000) - math.log(500)) * 100))
        scores["gdp_per_capita_score"] = round(pc_score, 1)

    # Debt score (inverted: lower debt = higher score; 150%+ → 0, 0% → 100)
    if debt is not None:
        debt_score = max(0, min(100, 100 - (debt / 150) * 100))
        scores["debt_score"] = round(debt_score, 1)

    # Inflation score (inverted: ~2% target is ideal; >20% → 0, 0% → 85, 2% → 100)
    if inflation is not None:
        if inflation <= 2:
            infl_score = 85 + (inflation / 2) * 15  # reward near-target
        else:
            infl_score = max(0, 100 - (inflation / 20) * 100)
        scores["inflation_score"] = round(min(100, infl_score), 1)

    # Unemployment score (inverted: 0% → 100, 20%+ → 0)
    if unemployment is not None:
        unemp_score = max(0, min(100, 100 - (unemployment / 20) * 100))
        scores["unemployment_score"] = round(unemp_score, 1)

    # Overall composite
    values = list(scores.values())
    scores["composite"] = round(sum(values) / len(values), 1) if values else 50.0
    return scores
