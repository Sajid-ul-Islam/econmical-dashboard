import csv
import json
import urllib.request
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1. Fetch countries list dynamically from World Bank API
print("Fetching list of all countries from World Bank API...", flush=True)
countries = []
try:
    url = "https://api.worldbank.org/v2/country?format=json&per_page=300"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        data = json.loads(response.read().decode("utf-8"))
        for c in data[1]:
            # Filter actual countries (exclude regions and aggregates)
            if c.get("region", {}).get("id") not in ["NA", ""] and c.get("capitalCity"):
                countries.append({"code": c["id"], "name": c["name"]})
except Exception as e:
    print(f"Failed to fetch country list dynamically: {e}. Using fallback countries list.", flush=True)
    countries = [
        {"code": "USA", "name": "United States"},
        {"code": "CHN", "name": "China"},
        {"code": "DEU", "name": "Germany"},
        {"code": "JPN", "name": "Japan"},
        {"code": "GBR", "name": "United Kingdom"},
        {"code": "FRA", "name": "France"},
        {"code": "IND", "name": "India"},
        {"code": "BRA", "name": "Brazil"},
        {"code": "BGD", "name": "Bangladesh"},
        {"code": "PAK", "name": "Pakistan"},
        {"code": "IDN", "name": "Indonesia"},
        {"code": "NGA", "name": "Nigeria"},
        {"code": "ZAF", "name": "South Africa"},
        {"code": "TUR", "name": "Turkey"},
        {"code": "SAU", "name": "Saudi Arabia"},
        {"code": "ARG", "name": "Argentina"},
        {"code": "MEX", "name": "Mexico"},
        {"code": "KOR", "name": "South Korea"},
        {"code": "CAN", "name": "Canada"},
        {"code": "AUS", "name": "Australia"},
        {"code": "RUS", "name": "Russia"},
        {"code": "EGY", "name": "Egypt"},
    ]

print(f"Found {len(countries)} countries.", flush=True)

indicators = {
    "gdp": "NY.GDP.MKTP.CD",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "debt_pct_gdp": "GC.DOD.TOTL.GD.ZS",
    "inflation": "FP.CPI.TOTL.ZG",
    "unemployment": "SL.UEM.TOTL.ZS",
    "life_expectancy": "SP.DYN.LE00.IN",
    "population": "SP.POP.TOTL",
}

os.makedirs("data", exist_ok=True)
csv_file = "data/economic_data_snapshot.csv"

existing_rows = {}
existing_lock = threading.Lock()

if os.path.exists(csv_file):
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row["country_code"], row["indicator"], row["year"])
                existing_rows[key] = row
    except Exception:
        pass

csv_lock = threading.Lock()

def save_rows(rows_dict):
    with csv_lock:
        try:
            with open(csv_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["country_code", "country_name", "indicator", "year", "value", "source", "fetched_at"])
                writer.writeheader()
                for row in sorted(rows_dict.values(), key=lambda r: (r["country_code"], r["indicator"], int(r["year"]))):
                    writer.writerow(row)
        except Exception as e:
            print(f"Error saving to CSV: {e}", flush=True)

tasks = []
for c in countries:
    for ind_name, ind_code in indicators.items():
        tasks.append((c["code"], c["name"], ind_name, ind_code))

total_reqs = len(tasks)
print(f"Total indicator-country pairs to process: {total_reqs}", flush=True)

completed = 0
completed_lock = threading.Lock()

def fetch_pair(ccode, cname, ind_name, ind_code):
    global completed
    
    with existing_lock:
        # Check if already fetched
        if any(k[0] == ccode and k[1] == ind_name for k in existing_rows.keys()):
            with completed_lock:
                completed += 1
            print(f"[{completed}/{total_reqs}] Skipping {ccode} {ind_name} (already in snapshot)", flush=True)
            return

    url = f"https://api.worldbank.org/v2/country/{ccode}/indicator/{ind_code}?format=json&per_page=100&mrv=40&date=1990:2026"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            new_data = False
            if len(data) >= 2 and data[1]:
                for item in data[1]:
                    if item.get("value") is not None:
                        val = float(item["value"])
                        year = str(item["date"])
                        row = {
                            "country_code": ccode,
                            "country_name": cname,
                            "indicator": ind_name,
                            "year": year,
                            "value": str(val),
                            "source": "World Bank API (Snapshot)",
                            "fetched_at": "2026-06-08T15:26:10Z"
                        }
                        with existing_lock:
                            existing_rows[(ccode, ind_name, year)] = row
                        new_data = True
            
            with completed_lock:
                completed += 1
            print(f"[{completed}/{total_reqs}] Fetched {ccode} {ind_name}", flush=True)
            if new_data:
                save_rows(existing_rows)
    except Exception as e:
        with completed_lock:
            completed += 1
        print(f"[{completed}/{total_reqs}] Error fetching {ccode} {ind_name}: {e}", flush=True)

# Run fetches in parallel using ThreadPoolExecutor (16 workers)
max_threads = 16
with ThreadPoolExecutor(max_workers=max_threads) as executor:
    futures = [executor.submit(fetch_pair, *task) for task in tasks]
    for future in as_completed(futures):
        pass

print("Done fetching all countries!", flush=True)
