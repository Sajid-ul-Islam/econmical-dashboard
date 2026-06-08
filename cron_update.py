"""
Scheduled task to refresh economic data in Supabase.
Designed to be run via GitHub Actions: python cron_update.py
Works without an active Streamlit runtime by monkey-patching st.cache_data.
"""

import os
import logging

# ── Patch Streamlit before any imports touch it ───────────────────────────
# st.cache_data and st.secrets are not available outside a Streamlit process.
# We replace them with no-op equivalents so all utils modules can be imported.
import streamlit as st

# Bypass @st.cache_data — just call the function directly
st.cache_data = lambda *args, **kwargs: (lambda fn: fn)
st.cache_resource = lambda *args, **kwargs: (lambda fn: fn)

# Load secrets from env vars when running in CI/CD
class _EnvSecrets:
    def get(self, key, default=None):
        val = os.environ.get(key.upper())
        if val is None:
            return default
        # Support nested keys via _SUPABASE_URL → secrets["supabase"]["url"]
        return val

    def __getitem__(self, key):
        val = os.environ.get(key.upper())
        if val is not None:
            return val
        # Return a sub-accessor for nested secret groups
        class _Section:
            def __init__(self, prefix):
                self.prefix = prefix
            def get(self, k, default=None):
                return os.environ.get(f"{self.prefix}_{k}".upper(), default)
            def __getitem__(self, k):
                v = os.environ.get(f"{self.prefix}_{k}".upper())
                if v is None:
                    raise KeyError(k)
                return v
        return _Section(key)

st.secrets = _EnvSecrets()

# Suppress st.warning / st.error output to stdout in CI
st.warning = lambda *a, **kw: logging.warning(str(a[0]) if a else "")
st.error = lambda *a, **kw: logging.error(str(a[0]) if a else "")
st.session_state = {}

# ── Now safe to import project modules ───────────────────────────────────
from utils.database import get_all_countries_in_db
from utils.data_fetcher import load_country_data, get_all_countries

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_update():
    logging.info("Starting scheduled data update...")

    db_countries = get_all_countries_in_db()
    codes_to_update = [c["country_code"] for c in db_countries if c["country_code"] != "WLD"]

    if not codes_to_update:
        logging.info("No countries in DB — using defaults.")
        codes_to_update = [
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
            "ROU", "SVK", "SVN", "ESP", "SWE", "TUR",
            "MEX", "PHL", "COD", "VNM", "THA",
            "ISR", "PRK"
        ]

    all_countries = {c["code"]: c["name"] for c in get_all_countries()}

    for code in codes_to_update:
        name = all_countries.get(code, code)
        logging.info(f"Refreshing {name} ({code})…")
        load_country_data(code, name, force=True)

    logging.info("✅ Scheduled data update complete.")


if __name__ == "__main__":
    run_update()
