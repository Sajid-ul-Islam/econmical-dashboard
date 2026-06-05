import streamlit as st

def render_sidebar():
    """Renders the global sidebar options across all pages."""
    from utils.data_fetcher import get_all_countries, load_country_data
    
    raw_countries = get_all_countries()
    # Sort by region first, then country name for logical dropdown grouping
    all_countries = sorted(raw_countries, key=lambda c: (c.get("region") or "Other", c["name"]))
    
    country_options = {f"{c.get('region') or 'Other'} • {c['name']}": c["code"] for c in all_countries}
    country_names = list(country_options.keys())

    indicator_options = {
        "Macro • GDP (Total)": "gdp",
        "Macro • GDP Per Capita": "gdp_per_capita",
        "Macro • Inflation (Annual %)": "inflation",
        "Macro • Unemployment Rate (%)": "unemployment",
        "Fiscal • Debt % of GDP": "debt_pct_gdp",
        "Markets • Gold Price (Global)": "gold_price",
    }

    with st.sidebar:
        st.markdown("## 📊 EconVision")
        st.markdown("<p style='color:#64748B;font-size:11px;'>Global Economic Intelligence</p>", unsafe_allow_html=True)
        st.divider()
        
        st.markdown("### ⚙️ Global Options")
        
        if "filter_mode" not in st.session_state:
            st.session_state.filter_mode = "Individual Countries"
        if "sel_individual" not in st.session_state:
            st.session_state.sel_individual = st.session_state.get("selected_countries", ["USA", "CHN", "DEU"])
        for key in ["sel_region", "sel_org", "sel_income"]:
            if key not in st.session_state:
                st.session_state[key] = []
        
        GROUPS = {
            "🌍 All North American": ["CAN", "USA", "MEX", "GTM", "BLZ", "HND", "SLV", "NIC", "CRI", "PAN", "CUB", "DOM", "HTI", "JAM", "TTO", "BRB"],
            "🌍 All South American": ["ARG", "BOL", "BRA", "CHL", "COL", "ECU", "GUY", "PRY", "PER", "SUR", "URY", "VEN"],
            "🌍 All Oceanian": ["AUS", "NZL", "FJI", "PNG", "SLB", "VUT", "WSM", "KIR", "TON", "FSM", "MHL", "PLW", "NRU", "TUV"],
            "🏛️ All NATO": ["ALB", "BEL", "BGR", "CAN", "HRV", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "ISL", "ITA", "LVA", "LTU", "LUX", "MNE", "MKD", "NLD", "NOR", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE", "TUR", "GBR", "USA"],
            "🏛️ All EU": ["AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"],
            "🏛️ All BRICS": ["BRA", "RUS", "IND", "CHN", "ZAF", "EGY", "ETH", "IRN", "ARE", "SAU"],
            "🏛️ All SAARC": ["AFG", "BGD", "BTN", "IND", "MDV", "NPL", "PAK", "LKA"],
            "🏛️ All OIC": ["AFG", "ALB", "DZA", "AGO", "BHR", "BGD", "BEN", "BFA", "BRN", "CMR", "TCD", "COM", "CIV", "DJI", "EGY", "GAB", "GMB", "GIN", "GNB", "GUY", "IDN", "IRN", "IRQ", "JOR", "KAZ", "KWT", "KGZ", "LBN", "LBY", "MYS", "MDV", "MLI", "MRT", "MAR", "MOZ", "NER", "NGA", "OMN", "PAK", "PSE", "QAT", "SAU", "SEN", "SLE", "SOM", "SDN", "SUR", "SYR", "TJK", "TGO", "TUN", "TUR", "TKM", "UGA", "ARE", "UZB", "YEM"],
            "🏛️ All Arab League": ["DZA", "BHR", "COM", "DJI", "EGY", "IRQ", "JOR", "KWT", "LBN", "LBY", "MRT", "MAR", "OMN", "PSE", "QAT", "SAU", "SOM", "SDN", "SYR", "TUN", "ARE", "YEM"],
            "🏛️ All OPEC": ["DZA", "AGO", "COG", "GNQ", "GAB", "IRN", "IRQ", "KWT", "LBY", "NGA", "SAU", "ARE", "VEN"],
            "🏛️ All G7": ["CAN", "FRA", "DEU", "ITA", "JPN", "GBR", "USA"],
            "🏛️ All G20": ["ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IND", "IDN", "ITA", "JPN", "KOR", "MEX", "RUS", "SAU", "ZAF", "TUR", "GBR", "USA"]
        }
        
        filter_modes = ["Individual Countries", "By Region", "By Organization", "By Income Level"]
        current_mode_index = filter_modes.index(st.session_state.filter_mode) if st.session_state.filter_mode in filter_modes else 0
        filter_mode = st.selectbox("Filter By:", filter_modes, index=current_mode_index)
        st.session_state.filter_mode = filter_mode
        
        final_codes = []
        valid_codes = [c["code"] for c in all_countries]
        
        if filter_mode == "Individual Countries":
            default_names = [name for name, code in country_options.items() if code in st.session_state.sel_individual]
            selected_names = st.multiselect(
                "Select Countries",
                options=["🌍 Select All", "❌ Clear All"] + country_names,
                default=default_names,
            )
            expanded = False
            temp_codes = []
            for n in selected_names:
                if n == "🌍 Select All":
                    temp_codes = valid_codes
                    expanded = True
                    break
                elif n == "❌ Clear All":
                    temp_codes = []
                    expanded = True
                    break
                else:
                    temp_codes.append(country_options[n])
                    
            st.session_state.sel_individual = temp_codes
            if expanded:
                st.rerun()
            final_codes = temp_codes

        elif filter_mode == "By Region":
            regions = ["Africa", "Asia", "Europe", "North America", "South America", "Oceania"]
            selected_regions = st.multiselect("Select Regions", options=regions, default=st.session_state.sel_region)
            st.session_state.sel_region = selected_regions
            for r in selected_regions:
                if r in ["North America", "South America", "Oceania"]:
                    final_codes.extend([c for c in GROUPS[f"🌍 All {r}"] if c in valid_codes])
                else:
                    final_codes.extend([c["code"] for c in all_countries if r in c.get("region", "")])

        elif filter_mode == "By Organization":
            orgs = ["NATO", "EU", "BRICS", "SAARC", "OIC", "Arab League", "OPEC", "G7", "G20"]
            selected_orgs = st.multiselect("Select Organizations", options=orgs, default=st.session_state.sel_org)
            st.session_state.sel_org = selected_orgs
            for o in selected_orgs:
                final_codes.extend([c for c in GROUPS[f"🏛️ All {o}"] if c in valid_codes])

        elif filter_mode == "By Income Level":
            incomes = ["High income", "Upper middle income", "Lower middle income", "Low income"]
            selected_incomes = st.multiselect("Select Income Levels", options=incomes, default=st.session_state.sel_income)
            st.session_state.sel_income = selected_incomes
            for i in selected_incomes:
                final_codes.extend([c["code"] for c in all_countries if c.get("income_level") == i])
                
        final_codes = list(dict.fromkeys(final_codes))
        st.session_state.selected_countries = final_codes
        
        default_inds = [k for k, v in indicator_options.items() if v in st.session_state.get("selected_indicators", ["gdp", "gdp_per_capita", "debt_pct_gdp"])]
        
        ind_special_options = ["🌍 Select All", "❌ Clear All", "📊 All Macro", "🏛️ All Fiscal", "💰 All Markets"]
        
        selected_ind_labels = st.multiselect(
            "Indicators",
            options=ind_special_options + list(indicator_options.keys()),
            default=default_inds,
        )
        
        final_inds = []
        ind_expanded = False
        valid_inds = list(indicator_options.values())
        
        for l in selected_ind_labels:
            if l == "🌍 Select All":
                final_inds = valid_inds
                ind_expanded = True
                break
            elif l == "❌ Clear All":
                final_inds = []
                ind_expanded = True
                break
            elif l == "📊 All Macro":
                final_inds.extend([v for k, v in indicator_options.items() if "Macro" in k])
                ind_expanded = True
            elif l == "🏛️ All Fiscal":
                final_inds.extend([v for k, v in indicator_options.items() if "Fiscal" in k])
                ind_expanded = True
            elif l == "💰 All Markets":
                final_inds.extend([v for k, v in indicator_options.items() if "Markets" in k])
                ind_expanded = True
            else:
                final_inds.append(indicator_options[l])
                
        final_inds = list(dict.fromkeys(final_inds))
        st.session_state.selected_indicators = final_inds
        
        if ind_expanded:
            st.rerun()
        
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