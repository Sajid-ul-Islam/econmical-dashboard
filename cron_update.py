"""
Scheduled task to refresh economic data in Supabase.
Designed to be run via GitHub Actions cron job.
"""

import logging
from utils.database import get_all_countries_in_db
from utils.data_fetcher import load_country_data, get_all_countries

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def run_update():
    logging.info("Starting scheduled data update...")
    
    db_countries = get_all_countries_in_db()
    # WLD is gold and is automatically fetched alongside other countries
    codes_to_update = [c["country_code"] for c in db_countries if c["country_code"] != "WLD"]
    
    if not codes_to_update:
        logging.info("No countries found in the database. Adding default countries.")
        codes_to_update = ["USA", "CHN", "DEU", "BGD"]
        
    all_countries = {c["code"]: c["name"] for c in get_all_countries()}
    
    for code in codes_to_update:
        name = all_countries.get(code, code)
        logging.info(f"Fetching updates for {name} ({code})...")
        load_country_data(code, name, force=True)
        
    logging.info("✅ Scheduled data update complete.")

if __name__ == "__main__":
    run_update()