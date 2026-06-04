# 🛠️ Analytical Skills (EconVision)

Beyond simple data visualization, the EconVision platform is equipped with several advanced analytical "skills" to help users derive meaningful macroeconomic insights.

## 1. 🔮 ML Time-Series Forecasting
The dashboard automatically generates 7-year forward-looking predictions for all economic indicators using Meta's **Prophet** algorithm.
- **How it works:** Fits historical data while handling non-linear growth trends and changepoints.
- **Confidence Intervals:** Generates 80% upper and lower bound confidence intervals to visualize uncertainty.
- **Fallback:** If the Prophet library is unavailable or fails due to insufficient data, it gracefully degrades to a standard 1st-degree polynomial linear trend projection.

## 2. 🚨 Statistical Anomaly Detection
Automatically scans historical data to flag unusual year-over-year (YoY) economic shifts.
- **How it works:** Calculates the YoY percentage growth for an indicator, computes the standard deviation and mean, and flags any data point with a **Z-score > 2.5**.
- **Use Case:** Instantly identifies massive economic contractions (like the 2008 Financial Crisis or 2020 COVID-19 pandemic) or explosive hyper-growth periods.

## 3. 🏆 Composite Economic Health Scoring
Condenses complex economic metrics into a single, intuitive 0-100 "Health Score" for easy country-to-country benchmarking.
- **How it works:** 
  - **GDP Growth (30%):** Rewards positive YoY trends.
  - **GDP Per Capita (30%):** Uses logarithmic scaling to normalize global wealth disparities (where $500 = 0, and $80,000+ = 100).
  - **Debt Ratio (25%):** Inversely weighted (lower Debt-to-GDP yields a higher score).
  - **Stability (15%):** Penalizes extreme volatility.

## 4. 🧪 Scenario Simulation (What-If Analysis)
Allows users to manually adjust growth trajectories to test economic hypotheses against the ML baselines.
- **How it works:** Users can tweak sliders for "Annual GDP Growth (%)" and "Debt Change per Year". The system recalculates compounding growth dynamically.
- **Comparison:** Plots the user's manual simulation alongside the Prophet ML baseline to quickly visualize the delta between current trends and hypothesized policies.

## 5. 🔬 Cross-Source Verification
Acts as an automated auditor for the database to ensure data integrity.
- **How it works:** Compares the cached data inside the Supabase database against a fresh, live payload from the World Bank API.
- **Drift Detection:** Flags any historical data point that has changed by >1% (which often happens when the World Bank retroactively revises historical GDP figures).