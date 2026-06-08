import os
import sys

# Ensure the root directory is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import cron_update to patch Streamlit before any other imports
import cron_update

from utils.data_fetcher import load_country_data, get_all_countries
from utils.forecasting import get_or_create_forecasts_batch
from utils.database import fetch_economic_data

# The 74 default countries (Top 2 & Bottom 2 of every continent + Muslim + BRICS + SAARC + OPEC + NATO)
countries = [
    "USA", "CAN", "BLZ", "HTI",
    "BRA", "ARG", "SUR", "GUY",
    "DEU", "GBR", "MNE", "ISL",
    "CHN", "JPN", "MDV", "BTN",
    "NGA", "ZAF", "COM", "DJI",
    "AUS", "NZL", "TUV", "NRU",
    "IDN", "SAU", "GMB", "SOM",
    "RUS", "IND", "EGY", "ETH", "IRN", "ARE",
    "AFG", "BGD", "NPL", "PAK", "LKA",
    "DZA", "AGO", "COG", "GNQ", "GAB", "IRQ", "KWT", "LBY", "VEN",
    "ALB", "BEL", "BGR", "HRV", "CZE", "DNK", "EST", "FIN", "FRA", "GRC",
    "HUN", "ITA", "LVA", "LTU", "LUX", "MKD", "NLD", "NOR", "POL", "PRT",
    "ROU", "SVK", "SVN", "ESP", "SWE", "TUR"
]

all_countries = {c["code"]: c["name"] for c in get_all_countries()}

print("Fetching historical data for 21 default countries...")
for code in countries:
    name = all_countries.get(code, code)
    print(f"Loading {name} ({code})...")
    load_country_data(code, name, force=True)

print("Batch pre-computing forecasts for all countries...")
# Load the data we just saved locally to compute the forecasts
df = fetch_economic_data(countries, ["gdp", "gdp_per_capita", "debt_pct_gdp", "inflation", "unemployment", "life_expectancy", "population"], 1990, 2026)
if not df.empty:
    print(f"Loaded {len(df)} rows from snapshot. Generating forecasts...")
    get_or_create_forecasts_batch(df, countries, ["gdp", "gdp_per_capita", "debt_pct_gdp", "inflation", "unemployment", "life_expectancy", "population"])
else:
    print("Error: Historical data is empty, cannot generate forecasts.")

print("Done! Defaults successfully fetched and cached to data/ folder.")
