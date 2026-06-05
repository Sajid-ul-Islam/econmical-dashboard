"""
Page 4 — Data Lab: provenance, data freshness, raw explorer, verification
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

st.set_page_config(page_title="Data Lab — EconVision", page_icon="🗄️", layout="wide")

from utils.ui import inject_custom_css
inject_custom_css()
from utils.ui import render_sidebar
render_sidebar()

from utils.database import get_supabase, get_all_countries_in_db
from utils.data_fetcher import (
    get_all_countries, get_country_data_cached,
    load_country_data, WB_INDICATORS, GOLD_INDICATOR
)
from utils.forecasting import detect_anomalies
from components.charts import format_value

countries = st.session_state.get("selected_countries", ["USA", "CHN"])
indicators = st.session_state.get("selected_indicators", ["gdp", "gdp_per_capita"])
year_range = st.session_state.get("year_range", (2000, 2026))

all_countries_list = get_all_countries()
country_map = {c["code"]: c["name"] for c in all_countries_list}

df = st.session_state.get("current_df", pd.DataFrame())

# ── Header ────────────────────────────────────────────────────────────────
st.markdown("## 🗄️ Data Lab")
st.caption("Data provenance, freshness tracking, raw explorer, and verification panel")
st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📋 Raw Data", "🔄 Freshness", "🔬 Verify", "📤 Export"])

# ── Tab 1: Raw Data Explorer ──────────────────────────────────────────────
with tab1:
    st.markdown("#### Raw Data Explorer")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_countries = st.multiselect(
            "Countries",
            options=countries,
            default=countries[:2],
            format_func=lambda c: country_map.get(c, c),
            key="raw_countries",
        )
    with col_f2:
        from components.charts import indicator_label
        filter_indicators = st.multiselect(
            "Indicators",
            options=indicators,
            default=indicators[:2],
            format_func=indicator_label,
            key="raw_indicators",
        )
    with col_f3:
        yr_min, yr_max = st.slider("Year Range", 1990, 2026, (2015, 2026), key="raw_year")

    if not df.empty and filter_countries and filter_indicators:
        raw = df[
            (df["country_code"].isin(filter_countries)) &
            (df["indicator"].isin(filter_indicators)) &
            (df["year"] >= yr_min) &
            (df["year"] <= yr_max)
        ].copy()
        
        # Apply same sorting logic as Dashboard
        kpi_indicator = indicators[0] if indicators else filter_indicators[0]
        latest_year = int(df["year"].max()) if not df.empty else 2026
        latest_df = df[(df["indicator"] == kpi_indicator) & (df["year"] == latest_year)]
        if not latest_df.empty:
            raw_ascending = st.session_state.get("sort_order", "Highest to Lowest") == "Lowest to Highest"
            sorted_codes = latest_df.sort_values("value", ascending=raw_ascending)["country_code"].tolist()
            ordered_countries = [c for c in sorted_codes if c in filter_countries] + [c for c in filter_countries if c not in sorted_codes]
            raw["country_code"] = pd.Categorical(raw["country_code"], categories=ordered_countries, ordered=True)
            
        raw = raw.sort_values(["country_code", "indicator", "year"], ascending=[True, True, False])

        display_raw = raw[["country_name", "country_code", "indicator", "year", "value", "source", "fetched_at"]].copy()
        display_raw["value_fmt"] = display_raw.apply(
            lambda r: format_value(r["value"], r["indicator"]) if pd.notna(r["value"]) else "—", axis=1
        )
        display_raw = display_raw.rename(columns={
            "country_name": "Country", "country_code": "Code",
            "indicator": "Indicator", "year": "Year",
            "value_fmt": "Value", "source": "Source", "fetched_at": "Fetched At",
        })
        display_raw = display_raw[["Country", "Code", "Indicator", "Year", "Value", "Source", "Fetched At"]]

        st.dataframe(display_raw, use_container_width=True, hide_index=True)
        st.caption(f"{len(raw)} rows")
    else:
        st.info("Select countries and indicators to explore raw data.")

# ── Tab 2: Data Freshness ─────────────────────────────────────────────────
with tab2:
    st.markdown("#### Data Freshness Dashboard")
    st.caption("Green = fresh (<24h) · Yellow = stale (>24h) · Red = missing")

    try:
        db = get_supabase()
        fresh_result = db.table("data_freshness").select("*").execute()
        if fresh_result.data:
            fresh_df = pd.DataFrame(fresh_result.data)
            now = datetime.now(timezone.utc)

            def freshness_badge(row):
                last = row.get("last_fetched")
                if not last:
                    return "🔴 Missing"
                try:
                    dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                    hours_ago = (now - dt).total_seconds() / 3600
                    if hours_ago < 24:
                        return f"🟢 Fresh ({hours_ago:.0f}h ago)"
                    elif hours_ago < 72:
                        return f"🟡 Stale ({hours_ago:.0f}h ago)"
                    else:
                        return f"🔴 Old ({hours_ago / 24:.0f}d ago)"
                except Exception:
                    return "⚪ Unknown"

            fresh_df["Status"] = fresh_df.apply(freshness_badge, axis=1)
            fresh_df["Country"] = fresh_df["country_code"].map(country_map).fillna(fresh_df["country_code"])
            display_fresh = fresh_df[["Country", "country_code", "indicator", "Status"]].rename(columns={
                "country_code": "Code", "indicator": "Indicator"
            })
            st.dataframe(display_fresh, use_container_width=True, hide_index=True)
        else:
            st.info("No freshness data yet. Load some data first.")
    except Exception as e:
        st.warning(f"Could not connect to database: {e}")

    st.divider()
    st.markdown("#### Force Refresh Selected Countries")
    refresh_codes = st.multiselect(
        "Select countries to force-refresh",
        options=countries,
        format_func=lambda c: country_map.get(c, c),
        key="refresh_select",
    )
    if st.button("🔄 Force Refresh Selected", use_container_width=False):
        with st.spinner("Refreshing..."):
            for code in refresh_codes:
                name = country_map.get(code, code)
                load_country_data(code, name, force=True)
        st.cache_data.clear()
        st.success(f"Refreshed {len(refresh_codes)} countries.")
        st.rerun()

# ── Tab 3: Data Verification ──────────────────────────────────────────────
with tab3:
    st.markdown("#### Cross-Source Verification")
    st.caption("Compare stored values against live World Bank API to detect drift")

    verify_country = st.selectbox(
        "Country to verify",
        options=countries,
        format_func=lambda c: country_map.get(c, c),
        key="verify_country",
    )
    verify_indicator = st.selectbox(
        "Indicator",
        options=[i for i in indicators if i in WB_INDICATORS],
        format_func=indicator_label,
        key="verify_indicator",
    )

    if st.button("🔬 Run Verification", use_container_width=False):
        with st.spinner("Fetching from World Bank for comparison..."):
            from utils.data_fetcher import fetch_world_bank
            wb_code = WB_INDICATORS.get(verify_indicator)
            live_rows = fetch_world_bank(wb_code, verify_country)

            if live_rows and not df.empty:
                live_df = pd.DataFrame(live_rows)[["year", "value"]].rename(columns={"value": "live_value"})
                stored = df[
                    (df["country_code"] == verify_country) &
                    (df["indicator"] == verify_indicator)
                ][["year", "value"]].rename(columns={"value": "stored_value"})

                merged = pd.merge(live_df, stored, on="year", how="inner")
                merged["delta_pct"] = ((merged["live_value"] - merged["stored_value"]) / merged["stored_value"].abs() * 100).round(2)
                merged["drift"] = merged["delta_pct"].abs() > 1.0

                drifted = merged[merged["drift"]]
                st.markdown(f"**{len(merged)} years compared · {len(drifted)} with >1% drift**")

                if drifted.empty:
                    st.success("✅ Stored data matches live source. No significant drift.")
                else:
                    st.warning(f"⚠️ {len(drifted)} years have >1% difference from live source.")
                    st.dataframe(
                        drifted[["year", "stored_value", "live_value", "delta_pct"]].rename(columns={
                            "year": "Year", "stored_value": "Stored", "live_value": "Live", "delta_pct": "Δ%"
                        }),
                        use_container_width=True,
                        hide_index=True,
                    )

                    if st.button("🔄 Update with Live Values"):
                        from utils.database import upsert_economic_data
                        from datetime import datetime, timezone
                        rows = [
                            {
                                "country_code": verify_country,
                                "country_name": country_map.get(verify_country, verify_country),
                                "indicator": verify_indicator,
                                "year": int(r["year"]),
                                "value": float(r["live_value"]),
                                "source": "World Bank API (verified)",
                                "fetched_at": datetime.now(timezone.utc).isoformat(),
                                "verified_at": datetime.now(timezone.utc).isoformat(),
                            }
                            for _, r in drifted.iterrows()
                        ]
                        upsert_economic_data(rows)
                        st.success("Updated drifted values.")
            else:
                st.info("Not enough data to compare.")

# ── Tab 4: Export ─────────────────────────────────────────────────────────
with tab4:
    st.markdown("#### Export Data")

    export_format = st.radio("Format", ["CSV", "JSON"], horizontal=True)

    if not df.empty:
        export_df = df[df["country_code"].isin(countries)].copy()
        export_df["value_formatted"] = export_df.apply(
            lambda r: format_value(r["value"], r["indicator"]) if pd.notna(r["value"]) else None, axis=1
        )

        if export_format == "CSV":
            csv = export_df[["country_name", "country_code", "indicator", "year", "value", "source"]].to_csv(index=False)
            st.download_button(
                "⬇️ Download CSV",
                data=csv,
                file_name="econvision_export.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            import json
            json_str = export_df[["country_name", "country_code", "indicator", "year", "value"]].to_json(orient="records", indent=2)
            st.download_button(
                "⬇️ Download JSON",
                data=json_str,
                file_name="econvision_export.json",
                mime="application/json",
                use_container_width=True,
            )

        # Predictions export
        pred_df = st.session_state.get("predictions_df", pd.DataFrame())
        if not pred_df.empty:
            pred_csv = pred_df.to_csv(index=False)
            st.download_button(
                "⬇️ Download Predictions CSV",
                data=pred_csv,
                file_name="econvision_predictions.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.info("No data loaded yet.")
