"""
AI Agent layer — Claude API with economic data context.
Uses in-context RAG: injects relevant data directly into the prompt.
No vector DB needed — data fits in Claude's context window.
"""

import streamlit as st
import anthropic
import pandas as pd
import json
from utils.database import log_query


SYSTEM_PROMPT = """You are an expert economic analyst AI assistant with deep knowledge in macroeconomics, development economics, and global finance.

You have access to a real-time economic database containing GDP, GDP per capita, government debt (% of GDP), and gold prices for countries worldwide, spanning from 1990 to present with ML-based projections to 2030.

When answering:
- Be precise with numbers, always cite the year
- Highlight trends, anomalies, and comparative insights
- Use economic reasoning to explain causes and effects
- When relevant, compare to historical patterns or other countries
- Flag data limitations honestly
- Structure longer answers with clear sections
- Format numbers clearly (e.g., $1.2T for trillion, $45K for thousands)

You ONLY answer questions related to economics, GDP, debt, gold, financial markets, development, and country comparisons. For unrelated questions, politely redirect.
"""


def build_data_context(
    df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    selected_countries: list[str],
    selected_indicators: list[str],
) -> str:
    """Build a concise data summary to inject into the prompt."""
    if df.empty:
        return "No data currently loaded in the database."

    lines = ["=== CURRENT DATABASE SNAPSHOT ===\n"]

    # Latest values per country per indicator
    latest_year = int(df["year"].max()) if not df.empty else 2023

    for country in selected_countries:
        cdf = df[df["country_code"] == country]
        if cdf.empty:
            continue
        cname = cdf["country_name"].iloc[0] if "country_name" in cdf.columns else country
        lines.append(f"\n{cname} ({country}):")

        for indicator in selected_indicators:
            idf = cdf[cdf["indicator"] == indicator].sort_values("year")
            if idf.empty:
                continue

            latest = idf[idf["year"] == idf["year"].max()]
            oldest_5 = idf.tail(5)

            unit = _get_unit(indicator)
            if not latest.empty:
                val = latest["value"].iloc[0]
                year = latest["year"].iloc[0]
                lines.append(f"  {indicator}: {_fmt(val, indicator)} {unit} ({year})")

            # 5-year trend
            if len(oldest_5) >= 2:
                trend_data = [f"{int(r['year'])}: {_fmt(r['value'], indicator)}" for _, r in oldest_5.iterrows()]
                lines.append(f"  Recent trend: {' → '.join(trend_data)}")

            # Prediction
            if not predictions_df.empty:
                pdf = predictions_df[
                    (predictions_df["country_code"] == country) &
                    (predictions_df["indicator"] == indicator)
                ].sort_values("year").head(5)
                if not pdf.empty:
                    pred_data = [f"{int(r['year'])}: {_fmt(r['predicted'], indicator)}" for _, r in pdf.iterrows()]
                    lines.append(f"  Forecast: {' → '.join(pred_data)}")

    lines.append(f"\nData range: 1990 - {latest_year} (historical) + up to 2031 (projected)")
    return "\n".join(lines)


def _fmt(value: float, indicator: str) -> str:
    if indicator == "gdp":
        if value >= 1e12:
            return f"${value/1e12:.2f}T"
        elif value >= 1e9:
            return f"${value/1e9:.1f}B"
        return f"${value:,.0f}"
    elif indicator == "gdp_per_capita":
        return f"${value:,.0f}"
    elif indicator == "debt_pct_gdp":
        return f"{value:.1f}%"
    elif indicator == "gold_price":
        return f"${value:,.0f}/oz"
    return f"{value:,.2f}"


def _get_unit(indicator: str) -> str:
    units = {
        "gdp": "USD",
        "gdp_per_capita": "USD/person",
        "debt_pct_gdp": "% of GDP",
        "gold_price": "USD/troy oz",
    }
    return units.get(indicator, "")


def ask_agent(
    user_query: str,
    df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    selected_countries: list[str],
    selected_indicators: list[str],
    conversation_history: list[dict],
) -> str:
    """
    Send query to Claude with full data context.
    Returns response string.
    """
    try:
        api_key = st.secrets.get("anthropic", {}).get("api_key", "")
        if not api_key:
            return "⚠️ Anthropic API key not configured. Add it to your Streamlit secrets."

        client = anthropic.Anthropic(api_key=api_key)

        data_context = build_data_context(df, predictions_df, selected_countries, selected_indicators)

        # Build messages with history
        messages = []
        for msg in conversation_history[-8:]:  # Keep last 8 turns
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add context + current query
        messages.append({
            "role": "user",
            "content": f"""Here is the current economic data context:

{data_context}

User question: {user_query}"""
        })

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        answer = response.content[0].text
        log_query(user_query, answer)
        return answer

    except anthropic.AuthenticationError:
        return "⚠️ Invalid Anthropic API key. Check your secrets configuration."
    except Exception as e:
        return f"⚠️ Agent error: {str(e)}"


SUGGESTED_QUESTIONS = [
    "Which country has the highest debt-to-GDP ratio?",
    "Compare GDP growth trends for selected countries over the last decade",
    "What does the GDP forecast suggest for these countries by 2030?",
    "How did gold prices correlate with the 2008 financial crisis?",
    "Which country has the best economic health based on current data?",
    "Explain the debt situation of the countries in context",
    "What are the key economic risks based on the current data?",
    "Compare GDP per capita — which country has improved the most?",
]
