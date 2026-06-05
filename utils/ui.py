import streamlit as st

def render_sidebar():
    """Renders the global sidebar options across all pages."""
    from utils.data_fetcher import get_all_countries, load_country_data
    
    all_countries = get_all_countries()
    country_options = {c["name"]: c["code"] for c in all_countries}
    country_names = list(country_options.keys())

    indicator_options = {
        "GDP (Total)": "gdp",
        "GDP Per Capita": "gdp_per_capita",
        "Debt % of GDP": "debt_pct_gdp",
        "Gold Price (Global)": "gold_price",
    }

    with st.sidebar:
        st.markdown("## 📊 EconVision")
        st.markdown("<p style='color:#64748B;font-size:11px;'>Global Economic Intelligence</p>", unsafe_allow_html=True)
        st.divider()
        
        st.markdown("### ⚙️ Global Options")
        
        default_names = [name for name, code in country_options.items() if code in st.session_state.get("selected_countries", ["USA", "CHN", "DEU"])]
        selected_names = st.multiselect(
            "Countries",
            options=country_names,
            default=default_names[:6],
            max_selections=8,
        )
        st.session_state.selected_countries = [country_options[n] for n in selected_names]
        
        default_inds = [k for k, v in indicator_options.items() if v in st.session_state.get("selected_indicators", ["gdp", "gdp_per_capita", "debt_pct_gdp"])]
        selected_ind_labels = st.multiselect(
            "Indicators",
            options=list(indicator_options.keys()),
            default=default_inds,
        )
        st.session_state.selected_indicators = [indicator_options[l] for l in selected_ind_labels]
        
        st.session_state.year_range = st.slider(
            "Year Range",
            min_value=1990,
            max_value=2031,
            value=st.session_state.get("year_range", (2000, 2026)),
            step=1,
        )

        st.session_state.sort_order = st.selectbox(
            "Sort Order (Primary Indicator)",
            options=["Highest to Lowest", "Lowest to Highest"],
            index=0 if st.session_state.get("sort_order", "Highest to Lowest") == "Highest to Lowest" else 1,
        )

        st.session_state.show_predictions = st.toggle(
            "Show ML Predictions",
            value=st.session_state.get("show_predictions", True),
        )

        if st.button("🔄 Refresh Data", use_container_width=True):
            with st.spinner("Fetching from World Bank & FRED..."):
                for code in st.session_state.selected_countries:
                    load_country_data(code, {v: k for k, v in country_options.items()}.get(code, code), force=True)
            st.cache_data.clear()
            st.success("Data refreshed!")
            st.rerun()
        
        st.divider()
        st.markdown("<p style='color:#374151;font-size:10px;text-align:center;margin-top:24px'>Sources: World Bank · FRED<br>ML: Prophet · Linear Trend<br>AI: Claude Sonnet</p>", unsafe_allow_html=True)

def inject_custom_css():
    """Injects a modern, glassmorphic UI theme across all Streamlit pages."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Mono', monospace;
        letter-spacing: -0.5px;
    }

    /* Main Background */
    .stApp { background: #0A0F1C; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #05080F !important;
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #94A3B8 !important;
        font-weight: 500;
    }

    /* Metric / KPI Cards (Glassmorphism) */
    [data-testid="metric-container"] {
        background: rgba(17, 24, 39, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    [data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        border-color: rgba(0, 212, 255, 0.4);
        box-shadow: 0 8px 15px rgba(0, 212, 255, 0.1);
    }
    [data-testid="metric-container"] label {
        color: #8B9BB4 !important;
        font-size: 12px !important;
        letter-spacing: 1px;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        color: #E2E8F0 !important;
        font-family: 'Space Mono', monospace;
        font-size: 1.8rem !important;
        font-weight: 700;
    }
    [data-testid="metric-container"] [data-testid="stMetricDelta"] {
        font-size: 13px !important;
        font-weight: 500;
    }

    /* Buttons (Neon Glow) */
    .stButton > button {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.1), rgba(0, 212, 255, 0.02));
        border: 1px solid rgba(0, 212, 255, 0.3);
        color: #00D4FF;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        border-radius: 8px;
        padding: 8px 16px;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.2), rgba(0, 212, 255, 0.05));
        border-color: #00D4FF;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
        color: #FFFFFF;
    }

    /* Tabs (Pill Shape) */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 8px;
        color: #94A3B8;
        padding: 8px 20px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(0, 212, 255, 0.1) !important;
        border-color: rgba(0, 212, 255, 0.4) !important;
        color: #00D4FF !important;
    }

    /* AI Chat UI */
    [data-testid="stChatMessage"] {
        background: rgba(17, 24, 39, 0.5);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    /* Differentiate User Messages */
    [data-testid="stChatMessage"]:has([data-testid="stIcon"][aria-label="🧑"]) {
        background: rgba(0, 212, 255, 0.03);
        border-color: rgba(0, 212, 255, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)