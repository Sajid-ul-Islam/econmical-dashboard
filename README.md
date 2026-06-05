# 📊 EconVision — Global Economic Intelligence Dashboard

A full-stack data science showcase project featuring real economic data, ML forecasting, AI agent, and multi-country comparisons. Built for Streamlit Cloud deployment.

**Live App:** [global-economics.streamlit.app](https://global-economics.streamlit.app)

## Features

| Feature | Details |
|---|---|
| 📈 **Live Data** | World Bank API (GDP, debt) + FRED API (gold prices) |
| 🔮 **ML Forecasting** | Prophet time-series predictions to 2031 with confidence intervals |
| 🌍 **World Map** | Choropleth visualisation of any indicator across all countries |
| 🔍 **Comparison** | Bar charts, correlation explorer, ranking tables |
| 🧪 **What-If Simulator** | Adjust growth/debt scenarios and project outcomes |
| 🚨 **Anomaly Detection** | Z-score based flagging of unusual economic changes |
| 🏆 **Health Scores** | Composite economic wellness index per country |
| 🤖 **AI Agent** | Claude-powered chat with in-context RAG over live data (Integrated in Data Lab) |
| 🗄️ **Data Lab** | Provenance, freshness tracking, cross-source verification, AI Agent |
| ⬇️ **Export** | CSV/JSON download of all data and predictions |

---

## Screenshots

![3D Multivariate Animation](https://placehold.co/800x400/111827/E2E8F0?text=3D+Multivariate+Animation+Screenshot)
*3D Multivariate Animation of Economic Indicators over time.*

---

## Setup

### 1. External Services (all free tiers)

#### Supabase (Database)
1. Go to [supabase.com](https://supabase.com) → New project (free tier)
2. Go to **SQL Editor** and run this to create tables:

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

3. Copy your **Project URL** and **anon/public API key** from Settings → API

#### FRED API Key (for gold prices)
1. Sign up free at [fred.stlouisfed.org](https://fred.stlouisfed.org/docs/api/api_key.html)
2. Request an API key (instant approval)

#### Anthropic API Key (for AI agent)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key (pay-as-you-go, very low cost for this use case)

---

### 2. Local Development

```bash
# Clone and install
git clone <your-repo>
cd econ-dashboard
pip install -r requirements.txt

# Configure secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your keys

# Run
streamlit run app.py
```

---

### 3. Streamlit Cloud Deployment

1. Push this folder to a **GitHub repository**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → select `app.py` as the main file
4. Under **Advanced Settings → Secrets**, paste:

```toml
[supabase]
url = "https://xxxx.supabase.co"
key = "your-anon-key"

[anthropic]
api_key = "sk-ant-..."

[fred]
api_key = "your-fred-key"
```

5. Deploy — done!

---

## Architecture

```
econ-dashboard/
├── app.py                    # Main entry + global sidebar
├── pages/
│   ├── 1_📈_Dashboard.py     # KPIs, timelines, anomalies, health scores
│   ├── 2_🔍_Compare.py       # Bar charts, correlation, rankings, what-if
│   ├── 3_🤖_AI_Agent.py      # Claude RAG chat interface
│   ├── 4_🗄️_Data_Lab.py      # Provenance, freshness, verification, export
│   └── 5_🌍_World_Map.py     # Choropleth world map
├── utils/
│   ├── data_fetcher.py       # World Bank + FRED APIs, stale check
│   ├── database.py           # Supabase CRUD operations
│   ├── forecasting.py        # Prophet + fallback forecasting, anomaly detection
│   └── agent.py              # Claude API + in-context RAG
├── components/
│   └── charts.py             # All Plotly chart components
├── requirements.txt
└── .streamlit/
    ├── config.toml           # Dark theme
    └── secrets.toml.example  # Template for secrets
```

## Data Sources & Freshness

| Source | Data | Update Freq | Key Required |
|---|---|---|---|
| World Bank API | GDP, GDP per capita, Debt/GDP | Quarterly | No |
| FRED (St. Louis Fed) | Gold price (annual avg) | Annual | Yes (free) |
| Fallback | Gold price (hardcoded historical) | Static | No |

Data auto-refreshes if >24 hours old. Use **Data Lab → Freshness** to monitor.

## Extending This Project

Ideas to take it further:
- Add **inflation (CPI)** and **unemployment** from World Bank
- Add **exchange rates** from FRED (free)
- Add **news sentiment** via NewsAPI + simple NLP
- Export a **country report PDF** using WeasyPrint
- Add **user accounts** via Supabase Auth
- Deploy a **scheduled Supabase Edge Function** to refresh data nightly

---

*Built as a data science + economics portfolio project. Sources: World Bank Open Data, FRED (Federal Reserve Bank of St. Louis), Anthropic Claude.*
