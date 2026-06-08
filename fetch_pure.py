import csv
import json
import urllib.request
import os
import sys

countries = [
    "USA", "CAN", "BLZ", "HTI",
    "BRA", "ARG", "SUR", "GUY",
    "DEU", "GBR", "MNE", "ISL",
    "CHN", "JPN", "MDV", "BTN",
    "NGA", "ZAF", "COM", "DJI",
    "AUS", "NZL", "TUV", "NRU",
    "IDN", "SAU", "GMB", "SOM"
]

indicators = {
    "gdp": "NY.GDP.MKTP.CD",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "debt_pct_gdp": "GC.DOD.TOTL.GD.ZS",
    "inflation": "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
    "life_expectancy": "SP.DYN.LE00.IN",
}

os.makedirs("data", exist_ok=True)
csv_file = "data/economic_data_snapshot.csv"

existing_rows = {}
if os.path.exists(csv_file):
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["country_code"], row["indicator"], row["year"])
                existing_rows[key] = row
    except Exception:
        pass

def save_rows(rows_dict):
    try:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["country_code", "country_name", "indicator", "year", "value", "source", "fetched_at"])
            writer.writeheader()
            for row in sorted(rows_dict.values(), key=lambda r: (r["country_code"], r["indicator"], int(r["year"]))):
                writer.writerow(row)
    except Exception as e:
        print(f"Error saving to CSV: {e}", flush=True)

total_reqs = len(countries) * len(indicators)
curr_req = 0

for ccode in countries:
    for ind_name, ind_code in indicators.items():
        curr_req += 1
        # Check if already fetched
        if any(k[0] == ccode and k[1] == ind_name for k in existing_rows.keys()):
            print(f"[{curr_req}/{total_reqs}] Skipping {ccode} {ind_name} (already in snapshot)", flush=True)
            continue
        url = f"https://api.worldbank.org/v2/country/{ccode}/indicator/{ind_code}?format=json&per_page=100&mrv=40&date=1990:2026"
        print(f"[{curr_req}/{total_reqs}] Fetching {ccode} {ind_name}...", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                if len(data) >= 2 and data[1]:
                    for item in data[1]:
                        if item.get("value") is not None:
                            val = float(item["value"])
                            year = str(item["date"])
                            cname = item["country"]["value"]
                            row = {
                                "country_code": ccode,
                                "country_name": cname,
                                "indicator": ind_name,
                                "year": year,
                                "value": str(val),
                                "source": "World Bank API (Snapshot)",
                                "fetched_at": "2026-06-08T15:26:10Z"
                            }
                            existing_rows[(ccode, ind_name, year)] = row
                    save_rows(existing_rows)
        except Exception as e:
            print(f"Error fetching {ccode} {ind_name}: {e}", flush=True)

print("Done fetching!", flush=True)
