---
title: EconVision
emoji: 📊
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.45.1"
python_version: 3.11
app_file: app.py
pinned: false
---
# 📊 EconVision — Global Economic Intelligence Dashboard

A full-stack data science portfolio project built on real economic data: live World Bank + FRED APIs, ML forecasting, AI chat agent, and interactive multi-country analysis. Deployed on Streamlit Cloud.

**Live App:** [global-economics.streamlit.app](https://global-economics.streamlit.app)

---

## Features

| Feature | Details |
|---|---|
| ⚡ **High Performance** | 90% reduction in database overhead via batched bulk upserts and Streamlit memory snapshots |
| 📈 **Live Data** | World Bank API (GDP, GDP per capita, debt, inflation, unemployment) + FRED (gold, silver, oil, DXY) |
| 🔮 **ML Forecasting** | Prophet time-series predictions to 2031 with 80% confidence intervals; linear trend fallback |
| 🌍 **World Map** | Animated choropleth across all countries — continuous scale or 5-tier debt risk categories |
| 🗺️ **Global Debt Coverage** | 173-country static debt snapshot (`data/global_debt_2024.csv`) fills map gaps instantly |
| 🔍 **Comparison** | Bar charts with debt threshold reference lines, correlation scatter (coloured by country), ranking tables |
| 🧪 **What-If Simulator** | Adjust GDP growth and debt trajectory; compare against Prophet ML baseline |
| 🚨 **Anomaly Detection** | Z-score based flagging of unusual year-over-year changes |
| 🏆 **Health Scores** | Composite 0–100 index from GDP per capita, debt, inflation, and unemployment |
| 🎲 **3D Animation** | Three-indicator multivariate scatter in 3D space with animated year progression |
| 📉 **Macro Trends** | USD purchasing power erosion (1970–2024) + Gold vs Silver dual-axis chart |
| 🤖 **AI Agent** | Claude-powered chat with in-context RAG, semantic cache, and 4-model fallback chain |
| 🗄️ **Data Lab** | Provenance tracking, freshness dashboard, cross-source verification, CSV/JSON export |

---

## Pages

| Page | Description |
|---|---|
| **Dashboard** | KPI cards, YoY deltas, health score gauges, timeline charts, anomaly flags |
| **Compare** | Bar comparisons, correlation explorer, ranking table, what-if simulator; auto-detects org group (NATO, G7, BRICS…) |
| **World Map** | Animated choropleth with risk-category toggle for debt indicator |
| **Data Lab** | Raw data explorer, freshness monitor, live verification, export, AI chat agent |
| **Macro Trends** | USD purchasing power chart, Gold vs Silver history with G/S ratio |

---

## Architecture

```
econ-dashboard/
├── app.py                     # Entry point + routing
├── pages/
│   ├── Dashboard.py           # KPIs, timelines, anomalies, health scores
│   ├── Compare.py             # Bar charts, correlation, rankings, what-if
│   ├── World_Map.py           # Choropleth world map with risk categories
│   ├── Data_Lab.py            # Provenance, freshness, verification, export, AI agent tab
│   └── Macro_Trends.py        # USD purchasing power + precious metals
├── components/
│   └── charts.py              # All Plotly components (timeline, bar, gauge, correlation, debt classify)
├── utils/
│   ├── data_fetcher.py        # World Bank + FRED APIs, static debt CSV loader
│   ├── database.py            # Supabase CRUD (upsert, fetch, freshness, query log)
│   ├── forecasting.py         # Prophet + linear fallback, anomaly detection, health score
│   ├── agent.py               # Claude RAG: context builder, semantic cache, model router
│   └── ui.py                  # Sidebar (countries, indicators, year range) + CSS theme
├── data/
│   └── global_debt_2024.csv   # 173-country static debt snapshot (IMF/WB 2024)
├── .streamlit/
│   ├── config.toml            # Dark theme config
│   └── secrets.toml.example   # Keys template
├── agent.md                   # AI Agent architecture documentation
├── skill.md                   # Analytical skills documentation
├── Dockerfile                 # Container build
├── docker-compose.yml         # Local container stack
├── requirements.txt
└── packages.txt
```

---

## Data Sources

| Source | Indicators | Refresh | API Key |
|---|---|---|---|
| World Bank API | GDP, GDP per capita, Debt/GDP, Inflation, Unemployment, Life Expectancy | Auto, 24h TTL | Not required |
| FRED (St. Louis Fed) | Gold price, Silver price, Brent oil, US Dollar Index (DXY) | Auto, 24h TTL | Free — [get one](https://fred.stlouisfed.org/docs/api/api_key.html) |
| Static CSV | Global debt snapshot (173 countries, 2024) | Fixed | Not required |

---

## Setup

### 1. Create Supabase tables

Go to [supabase.com](https://supabase.com) → new project → **SQL Editor** and run:

```sql
CREATE TABLE IF NOT EXISTS economic_data (
    id BIGSERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    country_name TEXT NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    value FLOAT,
    source TEXT,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ,
    UNIQUE (country_code, indicator, year)
);

CREATE TABLE IF NOT EXISTS predictions (
    id BIGSERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    year INTEGER NOT NULL,
    predicted FLOAT NOT NULL,
    lower_bound FLOAT,
    upper_bound FLOAT,
    model TEXT DEFAULT 'prophet',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (country_code, indicator, year, model)
);

CREATE TABLE IF NOT EXISTS data_freshness (
    id BIGSERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    indicator VARCHAR(50) NOT NULL,
    last_fetched TIMESTAMPTZ DEFAULT NOW(),
    last_verified TIMESTAMPTZ,
    status TEXT DEFAULT 'ok',
    UNIQUE (country_code, indicator)
);

CREATE TABLE IF NOT EXISTS query_log (
    id BIGSERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Copy your **Project URL** and **anon/public key** from Settings → API.

### 2. Local development

```bash
git clone https://github.com/Sajid-ul-Islam/econmical-dashboard.git
cd econ-dashboard
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Fill in your keys, then:
streamlit run app.py
```

### 3. Streamlit Cloud deployment

1. Push to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) → connect repo → main file: `app.py`.
3. Under **Advanced Settings → Secrets**, paste:

```toml
[supabase]
url = "https://xxxx.supabase.co"
key = "your-anon-key"

[anthropic]
api_key        = "sk-ant-..."
groq_key       = "gsk_..."
openrouter_key = "sk-or-..."
huggingface_key = "hf_..."

[fred]
api_key = "your-fred-key"
```

4. Deploy.

### 4. Docker (optional)

```bash
docker-compose up --build
# App runs at http://localhost:8501
```

---

## AI Agent

The agent uses **In-Context RAG** — it serialises the currently loaded DataFrame into a structured prompt and sends it with every query. No vector database required. It tries four providers in order (Claude → Groq → Gemini → OpenRouter) and reports which model answered. A TF-IDF semantic cache (threshold 0.97) avoids redundant API calls for repeated questions.

See [`agent.md`](agent.md) for full architecture details.

---

## Analytical Skills

See [`skill.md`](skill.md) for detailed documentation of all 9 analytical capabilities:

1. ML Time-Series Forecasting (Prophet + fallback)
2. Statistical Anomaly Detection (Z-score)
3. Composite Economic Health Scoring (4-factor)
4. Scenario Simulation / What-If Analysis
5. Cross-Source Verification (drift detection)
6. 3D Multivariate Animation
7. Debt Risk Classification (5-tier)
8. USD Purchasing Power Erosion
9. Precious Metals Comparison (Gold vs Silver)

---

*Sources: World Bank Open Data · FRED (Federal Reserve Bank of St. Louis) · IMF/WB debt estimates · BLS CPI data · Anthropic Claude*
