import streamlit as st

def _render_db_status():
    """Check database connection and display warning if offline."""
    from utils.database import get_supabase
    try:
        if get_supabase() is None:
            st.markdown(
                "<div style='background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); "
                "padding: 8px 12px; border-radius: 8px; margin-top: 10px; margin-bottom: 5px; font-size: 11px; color: #F59E0B; "
                "text-align: center; font-weight: 500;'>⚠️ Database Offline<br>Local Snapshot Active</div>",
                unsafe_allow_html=True
            )
    except Exception:
        pass

def _render_quick_presets():
    """Renders the Quick Presets panel for group selection."""
    with st.expander("🚀 Quick Presets", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏛️ G7 Nations", key="preset_g7", use_container_width=True):
                st.session_state.filter_mode = "By Organization"
                st.session_state.sel_org = ["G7"]
                st.session_state.selected_indicators = ["gdp", "gdp_per_capita", "debt_pct_gdp"]
                st.rerun()
            if st.button("⚔️ Nuclear Armed", key="preset_nuke", use_container_width=True):
                st.session_state.filter_mode = "By Organization"
                st.session_state.sel_org = ["Nuclear Armed"]
                st.session_state.selected_indicators = ["gdp", "debt_pct_gdp", "inflation"]
                st.rerun()
        with col2:
            if st.button("🏛️ BRICS Group", key="preset_brics", use_container_width=True):
                st.session_state.filter_mode = "By Organization"
                st.session_state.sel_org = ["BRICS"]
                st.session_state.selected_indicators = ["gdp", "population", "inflation"]
                st.rerun()
            if st.button("🇪🇺 Eurozone (EU)", key="preset_eu", use_container_width=True):
                st.session_state.filter_mode = "By Organization"
                st.session_state.sel_org = ["EU"]
                st.session_state.selected_indicators = ["gdp", "gdp_per_capita", "unemployment"]
                st.rerun()
        
        st.markdown("<p style='font-size:3px;margin:0;'></p>", unsafe_allow_html=True)
        col_rst, col_clr = st.columns(2)
        with col_rst:
            if st.button("🔄 Reset Defaults", key="preset_reset", use_container_width=True):
                st.session_state.filter_mode = "By Organization"
                st.session_state.selected_countries = ["USA", "RUS", "GBR", "FRA", "CHN", "IND", "PAK", "ISR", "PRK", "IRN"]
                st.session_state.selected_indicators = ["gdp", "gdp_per_capita", "debt_pct_gdp"]
                st.session_state.year_range = (2000, 2026)
                st.session_state.sel_individual = ["USA", "RUS", "GBR", "FRA", "CHN", "IND", "PAK", "ISR", "PRK", "IRN"]
                st.session_state.sel_org = ["Nuclear Armed"]
                st.session_state.sel_region = ["Europe"]
                st.session_state.sel_income = ["High income"]
                st.session_state.sort_order = "Highest to Lowest"
                st.session_state.show_predictions = True
                st.rerun()
        with col_clr:
            if st.button("🧹 Clear All", key="preset_clear", use_container_width=True):
                st.session_state.selected_countries = []
                st.session_state.sel_individual = []
                st.session_state.sel_org = []
                st.session_state.sel_region = []
                st.session_state.sel_income = []
                st.rerun()

def _init_session_states():
    """Initializes required state variables that haven't been set yet."""
    if "filter_mode" not in st.session_state:
        st.session_state.filter_mode = "By Organization"
    if "sel_individual" not in st.session_state:
        st.session_state.sel_individual = st.session_state.get(
            "selected_countries",
            [
                "USA", "RUS", "GBR", "FRA", "CHN", 
                "IND", "PAK", "ISR", "PRK", "IRN"
            ]
        )
    for key in ["sel_region", "sel_org", "sel_income"]:
        if key not in st.session_state:
            if key == "sel_org":
                st.session_state[key] = ["Nuclear Armed"]
            elif key == "sel_region":
                st.session_state[key] = ["Europe"]
            elif key == "sel_income":
                st.session_state[key] = ["High income"]

def _render_country_filters(all_countries, country_options, country_names):
    """Renders all filter logic for active countries."""
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
        "🏛️ All G20": ["ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IND", "IDN", "ITA", "JPN", "KOR", "MEX", "RUS", "SAU", "ZAF", "TUR", "GBR", "USA"],
        "🏛️ All Nuclear Armed": ["USA", "RUS", "GBR", "FRA", "CHN", "IND", "PAK", "ISR", "PRK", "IRN"],
        "🏛️ All Top Oil Producers": ["USA", "SAU", "RUS", "CAN", "CHN", "IRQ", "ARE", "BRA", "IRN", "KWT", "NOR", "MEX", "VEN", "NGA"],
        "🏛️ All Top Populated": ["CHN", "IND", "USA", "IDN", "PAK", "NGA", "BRA", "BGD", "RUS", "MEX", "ETH", "JPN", "PHL", "EGY", "COD", "VNM", "TUR", "IRN", "DEU", "THA"]
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
        selected_regions = st.multiselect(
            "Select Regions",
            options=["🌍 Select All", "❌ Clear All"] + regions,
            default=st.session_state.sel_region
        )
        region_expanded = False
        temp_regions = []
        for r in selected_regions:
            if r == "🌍 Select All":
                temp_regions = regions
                region_expanded = True
                break
            elif r == "❌ Clear All":
                temp_regions = []
                region_expanded = True
                break
            else:
                temp_regions.append(r)
        st.session_state.sel_region = temp_regions
        if region_expanded:
            st.rerun()
        for r in temp_regions:
            if r in ["North America", "South America", "Oceania"]:
                final_codes.extend([c for c in GROUPS[f"🌍 All {r}"] if c in valid_codes])
            else:
                final_codes.extend([c["code"] for c in all_countries if r in c.get("region", "")])

    elif filter_mode == "By Organization":
        orgs = ["NATO", "EU", "BRICS", "SAARC", "OIC", "Arab League", "OPEC", "G7", "G20", "Nuclear Armed", "Top Oil Producers", "Top Populated"]
        selected_orgs = st.multiselect(
            "Select Organizations",
            options=["🏛️ Select All", "❌ Clear All"] + orgs,
            default=st.session_state.sel_org
        )
        org_expanded = False
        temp_orgs = []
        for o in selected_orgs:
            if o == "🏛️ Select All":
                temp_orgs = orgs
                org_expanded = True
                break
            elif o == "❌ Clear All":
                temp_orgs = []
                org_expanded = True
                break
            else:
                temp_orgs.append(o)
        st.session_state.sel_org = temp_orgs
        if org_expanded:
            st.rerun()
        for o in temp_orgs:
            final_codes.extend([c for c in GROUPS[f"🏛️ All {o}"] if c in valid_codes])

    elif filter_mode == "By Income Level":
        incomes = ["High income", "Upper middle income", "Lower middle income", "Low income"]
        selected_incomes = st.multiselect(
            "Select Income Levels",
            options=["💰 Select All", "❌ Clear All"] + incomes,
            default=st.session_state.sel_income
        )
        income_expanded = False
        temp_incomes = []
        for i in selected_incomes:
            if i == "💰 Select All":
                temp_incomes = incomes
                income_expanded = True
                break
            elif i == "❌ Clear All":
                temp_incomes = []
                income_expanded = True
                break
            else:
                temp_incomes.append(i)
        st.session_state.sel_income = temp_incomes
        if income_expanded:
            st.rerun()
        for i in temp_incomes:
            final_codes.extend([c["code"] for c in all_countries if c.get("income_level") == i])
            
    final_codes = list(dict.fromkeys(final_codes))
    st.session_state.selected_countries = final_codes

    # Empty Selection Recovery Warning
    if not final_codes:
        st.markdown(
            "<div style='background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); "
            "padding: 10px; border-radius: 8px; font-size: 11px; color: #F87171; text-align: center; "
            "font-weight: 500; margin-bottom: 12px; margin-top: 10px;'>⚠️ No countries selected! The dashboard is empty.</div>",
            unsafe_allow_html=True
        )
        if st.button("🔌 Load Default Group (Nuclear Armed)", key="load_default_btn", use_container_width=True):
            st.session_state.filter_mode = "By Organization"
            st.session_state.sel_org = ["Nuclear Armed"]
            st.rerun()
    
    # Display list of active countries in the sidebar
    if final_codes:
        cnames_map = {c["code"]: c["name"] for c in all_countries}
        active_names = [cnames_map.get(code, code) for code in final_codes]
        display_limit = 5
        display_str = ", ".join(active_names[:display_limit])
        if len(active_names) > display_limit:
            display_str += f" (+{len(active_names) - display_limit} more)"
        st.markdown(
            f"<p style='color:#00D4FF;font-size:11px;margin-top:-8px;margin-bottom:12px;'><b>Active ({len(final_codes)}):</b> {display_str}</p>",
            unsafe_allow_html=True
        )

def _render_indicator_filters(indicator_options):
    """Renders multi-select indicator filters and predefined macro groups."""
    default_inds = [k for k, v in indicator_options.items() if v in st.session_state.get("selected_indicators", ["gdp", "gdp_per_capita", "debt_pct_gdp"])]
    
    ind_special_options = ["🌍 Select All", "❌ Clear All", "📊 All Macro", "🏛️ All Fiscal", "👥 All Social"]
    
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
        elif l == "👥 All Social":
            final_inds.extend([v for k, v in indicator_options.items() if "Social" in k])
            ind_expanded = True
        else:
            final_inds.append(indicator_options[l])
            
    final_inds = list(dict.fromkeys(final_inds))
    st.session_state.selected_indicators = final_inds
    
    if ind_expanded:
        st.rerun()

def _render_global_settings(country_options):
    """Renders UI controllers for Year Range, Sort Order, Predictions flag, and explicit API Refresh."""
    from utils.data_fetcher import load_country_data
    
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

def _render_ai_agent(active_page):
    """Renders the UI elements and interaction logic for the AI assistant chatbot in the sidebar."""
    st.divider()
    st.markdown("### 🤖 AI Economic Agent")
    
    # Display active page context in a small muted text
    if active_page:
        st.markdown(f"<p style='color:#00D4FF;font-size:11px;margin-bottom:0;'>Context: {active_page} Page</p>", unsafe_allow_html=True)
        st.session_state.active_page = active_page
    else:
        st.markdown("<p style='color:#64748B;font-size:11px;margin-bottom:0;'>Context: General Database</p>", unsafe_allow_html=True)
        
    # Chat history reset / API key layout
    col_clear, col_key = st.columns([1.2, 1])
    with col_clear:
        if st.button("🗑️ Clear Chat", key="clear_chat_sidebar", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    with col_key:
        show_key_input = st.toggle("🔑 Key", value=False, key="toggle_key_sidebar")

    if show_key_input:
        st.text_input(
            "Custom Anthropic API Key",
            type="password",
            key="custom_anthropic_key",
            help="Enter your Anthropic API key to use Claude 3.5 Sonnet.",
        )

    # Suggested Questions
    from utils.agent import SUGGESTED_QUESTIONS, ask_agent
    with st.expander("💡 Suggested Questions", expanded=False):
        for i, q in enumerate(SUGGESTED_QUESTIONS):
            if st.button(q, key=f"sq_sidebar_{i}", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": q})
                with st.spinner("Analyzing..."):
                    import pandas as pd
                    df = st.session_state.get("current_df", pd.DataFrame())
                    predictions_df = st.session_state.get("predictions_df", pd.DataFrame())
                    countries = st.session_state.get("selected_countries", [])
                    indicators = st.session_state.get("selected_indicators", [])
                    
                    response, model = ask_agent(
                        q, df, predictions_df, countries, indicators,
                        st.session_state.chat_history[:-1],
                        active_page=active_page
                    )
                st.session_state.chat_history.append({"role": "assistant", "content": response, "model": model})
                st.rerun()

    # Chat history display
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.session_state.chat_history:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "📊"):
                st.markdown(f"<div style='font-size: 13px;'>{msg['content']}</div>", unsafe_allow_html=True)
                if msg.get("model"):
                    if "Claude" not in msg["model"] and "Cache" not in msg["model"] and "Error" not in msg["model"]:
                        st.markdown(f"<p style='color:#F59E0B;font-size:9px;margin-top:4px;'>⚠️ Fallback: {msg['model']}</p>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<p style='color:#10B981;font-size:9px;margin-top:4px;'>⚡ {msg['model']}</p>", unsafe_allow_html=True)

    # Chat input form
    with st.form("sidebar_chat_form", clear_on_submit=True):
        prompt = st.text_input("Ask about this page or data:", placeholder="Type a question...", key="sidebar_prompt_input")
        submitted = st.form_submit_button("Send", use_container_width=True)

    if submitted and prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.spinner("Analyzing..."):
            import pandas as pd
            df = st.session_state.get("current_df", pd.DataFrame())
            predictions_df = st.session_state.get("predictions_df", pd.DataFrame())
            countries = st.session_state.get("selected_countries", [])
            indicators = st.session_state.get("selected_indicators", [])
            
            response, model = ask_agent(
                prompt, df, predictions_df, countries, indicators,
                st.session_state.chat_history[:-1],
                active_page=active_page
            )
        st.session_state.chat_history.append({"role": "assistant", "content": response, "model": model})
        st.rerun()

    st.divider()
    st.markdown("<p style='color:#374151;font-size:10px;text-align:center;margin-top:24px'>Sources: World Bank · FRED<br>ML: Prophet · Linear Trend<br>AI: Claude Sonnet</p>", unsafe_allow_html=True)

def render_sidebar(active_page: str = None):
    """Renders the global sidebar options across all pages."""
    from utils.data_fetcher import get_all_countries
    
    raw_countries = get_all_countries()
    # Sort alphabetically by country name
    all_countries = sorted(raw_countries, key=lambda c: c["name"])
    
    country_options = {c["name"]: c["code"] for c in all_countries}
    country_names = list(country_options.keys())

    indicator_options = {
        "Macro • GDP (Total)": "gdp",
        "Macro • GDP Per Capita": "gdp_per_capita",
        "Macro • Inflation (Annual %)": "inflation",
        "Macro • Unemployment Rate (%)": "unemployment",
        "Fiscal • Debt % of GDP": "debt_pct_gdp",
        "Social • Life Expectancy": "life_expectancy",
        "Social • Population": "population",
    }

    with st.sidebar:
        st.markdown("## 📊 EconVision")
        st.markdown("<p style='color:#64748B;font-size:11px;'>Global Economic Intelligence</p>", unsafe_allow_html=True)
        
        _render_db_status()
        st.divider()
        
        st.markdown("### ⚙️ Global Options")
        
        _render_quick_presets()
        _init_session_states()
        _render_country_filters(all_countries, country_options, country_names)
        _render_indicator_filters(indicator_options)
        _render_global_settings(country_options)
        _render_ai_agent(active_page)

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
    [data-testid="metric-container"], .glass-chart-card {
        background: rgba(17, 24, 39, 0.6);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    [data-testid="metric-container"] {
        padding: 16px 20px;
    }
    .glass-chart-card {
        padding: 20px;
        height: 100%; /* Ensure cards in a row have same height */
    }
    [data-testid="metric-container"]:hover, .glass-chart-card:hover {
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
    
    /* Sidebar Chat compacting */
    [data-testid="stSidebar"] [data-testid="stChatMessage"] {
        padding: 8px 12px !important;
        margin-bottom: 8px !important;
        border-radius: 8px !important;
    }
    [data-testid="stSidebar"] [data-testid="stChatMessage"] p {
        font-size: 13px !important;
        line-height: 1.4 !important;
    }

    /* Responsive layout adjustments for mobile/small screens */
    @media (max-width: 768px) {
        /* Optimize block container padding on mobile to save screen space */
        [data-testid="block-container"] {
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* Stack columns in the main area on mobile to prevent squashing */
        [data-testid="stAppViewContainer"] [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 16px !important;
        }
        
        /* Adjust font sizes in metric cards on mobile */
        [data-testid="metric-container"] [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
        }
        
        /* Compact typography for smaller screens */
        h1, h2, h3 {
            font-size: 1.4rem !important;
        }
        h4, h5, h6 {
            font-size: 1.1rem !important;
        }
        .stMarkdown [data-testid="stMarkdownContainer"] p {
            font-size: 13px !important;
        }
        
        /* Make tabs scroll horizontally on mobile instead of wrapping poorly */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            white-space: nowrap !important;
            flex-wrap: nowrap !important;
            gap: 4px !important;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 6px 12px !important;
            font-size: 13px !important;
        }
    }

    /* Skeleton Loaders */
    @keyframes pulse-bg {
        0% { background-color: rgba(17, 24, 39, 0.4); }
        50% { background-color: rgba(31, 41, 55, 0.6); }
        100% { background-color: rgba(17, 24, 39, 0.4); }
    }
    .skeleton-chart {
        height: 350px;
        width: 100%;
        border-radius: 12px;
        animation: pulse-bg 1.5s infinite ease-in-out;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 1rem;
    }
    .skeleton-kpi {
        height: 100px;
        width: 100%;
        border-radius: 12px;
        animation: pulse-bg 1.5s infinite ease-in-out;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)