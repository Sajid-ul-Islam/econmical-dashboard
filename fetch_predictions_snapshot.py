import pandas as pd
import numpy as np
import os
import csv
from datetime import datetime, timezone

snapshot_path = "data/economic_data_snapshot.csv"
output_path = "data/predictions_snapshot.csv"

def run_prophet_forecast(series_df, country_code, indicator, forecast_years=7):
    try:
        from prophet import Prophet
        import logging
        logging.getLogger("prophet").setLevel(logging.ERROR)
        logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
    except ImportError:
        return run_linear_forecast(series_df, country_code, indicator, forecast_years)

    series = series_df[["year", "value"]].dropna().copy()
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

        last_year = int(series["year"].max())
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
    except Exception:
        return run_linear_forecast(series_df, country_code, indicator, forecast_years)

def run_linear_forecast(series_df, country_code, indicator, forecast_years=7):
    series = series_df[["year", "value"]].dropna().copy()
    if len(series) < 3:
        return None

    x = series["year"].values
    y = series["value"].values
    coeffs = np.polyfit(x, y, 1)
    trend = np.poly1d(coeffs)

    residuals = y - trend(x)
    std = residuals.std()

    last_year = int(series["year"].max())
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

def main():
    if not os.path.exists(snapshot_path):
        print(f"Error: {snapshot_path} does not exist. Run fetch_pure.py first.", flush=True)
        return

    # Load existing prediction keys to skip duplicate work
    existing_keys = set()
    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_keys.add((row["country_code"], row["indicator"]))
        except Exception:
            pass

    df = pd.read_csv(snapshot_path)
    groups = df.groupby(["country_code", "indicator"])
    total = len(groups)
    current = 0

    print(f"Starting forecasting on {total} series...", flush=True)

    file_exists = os.path.exists(output_path)
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["country_code", "indicator", "year", "predicted", "lower_bound", "upper_bound", "model", "created_at"])
        if not file_exists or os.path.getsize(output_path) == 0:
            writer.writeheader()

        for (ccode, indicator), group in groups:
            current += 1
            if (ccode, indicator) in existing_keys:
                print(f"[{current}/{total}] Skipping {ccode} {indicator} (already cached)", flush=True)
                continue

            print(f"[{current}/{total}] Forecasting {ccode} {indicator}...", flush=True)
            pred_df = run_prophet_forecast(group, ccode, indicator)
            if pred_df is not None and not pred_df.empty:
                for row in pred_df.to_dict("records"):
                    writer.writerow(row)
                f.flush()

    print("Successfully completed forecasting and saved snapshots!", flush=True)

if __name__ == "__main__":
    main()
