# 🛠️ Analytical Skills (EconVision)

Beyond simple data visualisation, EconVision ships a suite of analytical skills that turn raw macroeconomic data into actionable insight.

---

## 1. 🔮 ML Time-Series Forecasting

Automatically generates 7-year forward predictions for every economic indicator.

- **Primary model:** Meta **Prophet** — handles non-linear trends, structural breaks, and changepoints.
- **Confidence bands:** 80% upper/lower bounds rendered as shaded regions on every timeline chart.
- **Fallback:** If Prophet is unavailable or the series is too short (<5 points), degrades gracefully to a 1st-degree polynomial linear trend with a residual-based uncertainty band.
- **Storage:** Forecasts are persisted to Supabase (`predictions` table) so they are not recomputed on every page load.
- **Batch Architecture:** Optimised to fetch and compute missing forecast combinations in bulk, drastically reducing database roundtrips.

---

## 2. 🚨 Statistical Anomaly Detection

Automatically scans historical series for unusual year-over-year shifts.

- **Method:** YoY % growth → Z-score standardisation. Any point with |Z| > 2.5 is flagged.
- **Output:** Annotated warnings on the Dashboard page, surfaced per country and indicator.
- **Catches:** 2008 financial crisis contractions, 2020 COVID collapses, hyperinflation spikes, and World Bank retroactive revisions.

---

## 3. 🏆 Composite Economic Health Scoring

Condenses four indicators into a single 0–100 score, rendered as a gauge chart per country.

| Component | Weight | Method |
|---|---|---|
| GDP per capita | ~30% | Log scale: $500 → 0, $80 000 → 100 |
| Debt/GDP | ~25% | Inverted: 0% debt → 100, 150%+ → 0 |
| Inflation | ~25% | Penalises deviation from 2% target; >20% → 0 |
| Unemployment | ~20% | Inverted: 0% → 100, 20%+ → 0 |

Score is recomputed live from whichever indicators are currently loaded — components are averaged only over available data.

---

## 4. 🧪 Scenario Simulation (What-If Analysis)

Users tweak GDP growth rate and debt trajectory sliders; the tool projects compounding outcomes over 5–20 years.

- Plots the **manual scenario** against the **Prophet ML baseline** on the same chart.
- Reports scenario vs baseline delta at the projection horizon as a metric card.
- Uses the last available historical year as the base value so projections are always anchored to real data.

---

## 5. 🔬 Cross-Source Verification

Automated data integrity auditor in **Data Lab → Verify**.

- Re-fetches the selected country/indicator from the live World Bank API.
- Merges against the cached Supabase copy and computes `Δ%` per year.
- Any year with >1% drift is flagged; a one-click button updates the stored value with the live figure.
- Catches World Bank retroactive GDP revisions, a real and common occurrence.

---

## 6. 🎲 3D Multivariate Animation

Dynamic visual comparison of three indicators simultaneously across selected countries.

- Plots each country as a chronological trajectory in 3D space with animated year markers.
- Adds connecting lines to trace each country's historical path.
- Reveals complex relationships — e.g. how debt scales relative to GDP per capita over decades — that are invisible in flat 2D charts.
- Requires at least 3 indicators loaded simultaneously.

---

## 7. 🌍 Debt Risk Classification

Categorises every country's debt-to-GDP ratio into a 5-tier risk system.

| Tier | Threshold | Colour |
|---|---|---|
| Low | < 30% | Teal `#2ecc71` |
| Moderate | 30–60% | Green `#388e3c` |
| Elevated | 60–90% | Orange `#f57c00` |
| High | 90–200% | Red `#d32f2f` |
| Critical | > 200% | Dark red `#8b0000` |

Used in two places: the **World Map risk-category choropleth** (toggle between categorical and continuous colour modes) and the **comparison bar chart** (Maastricht 60% and High Risk 90% reference lines).

The map is populated from a 173-country static CSV snapshot (`data/global_debt_2024.csv`) when live API coverage is sparse, ensuring global coverage on first load without any additional API calls.

---

## 8. 💵 USD Purchasing Power Erosion

Long-run narrative chart in **Macro Trends → USD Purchasing Power**.

- Computes cumulative purchasing power from a user-selectable base year (1970–2010) using compounded inverse CPI.
- Dual-axis: annual inflation bars (colour-coded green/orange/red by severity) + purchasing power line with area fill.
- Key metrics: current value of $100 from base year, cumulative erosion %, peak inflation year, and average annual rate.

---

## 9. 🥇 Precious Metals Comparison

**Macro Trends → Gold vs Silver** tab.

- Dual-axis chart: gold area fill (1970–2025) + silver dashed line + optional Gold/Silver ratio overlay.
- Historical event annotations: Hunt Brothers squeeze, 2008 crisis, 2011 all-time high, COVID rally, 2025 new ATH ($3,380).
- G/S ratio above ~80× historically signals silver is relatively undervalued — surfaced as a metric card alongside spot prices.
