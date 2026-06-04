"""
AI Agent layer — Claude API with economic data context.
Uses in-context RAG: injects relevant data directly into the prompt.
No vector DB needed — data fits in Claude's context window.
"""

import streamlit as st
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
import requests
import pandas as pd
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from utils.database import log_query, get_recent_queries


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


def check_semantic_cache(user_query: str, threshold: float = 0.92) -> str | None:
    """Check if a semantically similar query exists in the recent logs using a TF-IDF vectorized knowledge base."""
    logs_df = get_recent_queries(limit=200)
    if logs_df.empty or "query" not in logs_df.columns:
        return None

    queries = logs_df["query"].tolist()
    responses = logs_df["response"].tolist()
    
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(queries + [user_query])
        
        # Compare the last element (user_query) with all previous queries
        cosine_similarities = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
        best_match_idx = cosine_similarities.argmax()
        
        if cosine_similarities[best_match_idx] >= threshold:
            return responses[best_match_idx]
    except Exception:
        pass
    return None


def ask_agent(
    user_query: str,
    df: pd.DataFrame,
    predictions_df: pd.DataFrame,
    selected_countries: list[str],
    selected_indicators: list[str],
    conversation_history: list[dict],
) -> tuple[str, str]:
    """
    Send query to AI agent with full data context, returning (response, model_name).
    Checks available keys in secrets and falls back if one fails.
    """
    # 0. Check Semantic Cache (Vectorized KB) to save API costs
    cached_response = check_semantic_cache(user_query)
    if cached_response:
        return cached_response, "⚡ Semantic Cache (Vectorized KB)"

    secrets = st.secrets.get("anthropic", {})
    anthropic_key = secrets.get("api_key", "")
    groq_key = secrets.get("groq_key", "")
    gemini_key = secrets.get("gemini_key", "")
    openrouter_key = secrets.get("openrouter_key", "")
    hf_key = secrets.get("huggingface_key", "")

    data_context = build_data_context(df, predictions_df, selected_countries, selected_indicators)

    # Build messages with history
    messages = []
    for msg in conversation_history[-8:]:  # Keep last 8 turns
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add context + current query
    messages.append({
        "role": "user",
        "content": f"Here is the current economic data context:\n\n{data_context}\n\nUser question: {user_query}"
    })

    errors = []

    # 1. Try Anthropic (Claude 3.5 Sonnet)
    if anthropic_key and not anthropic_key.startswith("your-"):
        if HAS_ANTHROPIC:
            try:
                client = anthropic.Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    system=SYSTEM_PROMPT,
                    messages=messages,
                )
                answer = response.content[0].text
                log_query(user_query, answer)
                return answer, "Claude 3.5 Sonnet (Anthropic)"
            except Exception as e:
                errors.append(f"Anthropic error: {str(e)}")
        else:
            if "anthropic_warning_shown" not in st.session_state:
                st.warning("⚠️ Anthropic library is missing! Skipping Claude 3.5 Sonnet.", icon="⚠️")
                st.session_state.anthropic_warning_shown = True
            errors.append("Anthropic library missing.")

    # 2. Try Groq (Llama 3 70B)
    if groq_key:
        try:
            headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
            payload = {
                "model": "llama3-70b-8192",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
                "max_tokens": 1500
            }
            r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            answer = r.json()["choices"][0]["message"]["content"]
            log_query(user_query, answer)
            return answer, "Llama 3 70B (Groq)"
        except Exception as e:
            errors.append(f"Groq error: {str(e)}")

    # 3. Try Gemini (1.5 Flash)
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            # Combine history into a single string for Gemini to avoid strict alternating role constraints
            combined_chat = f"System: {SYSTEM_PROMPT}\n\n"
            for m in messages:
                combined_chat += f"{m['role'].capitalize()}: {m['content']}\n\n"
            
            payload = {"contents": [{"parts": [{"text": combined_chat}]}]}
            r = requests.post(url, json=payload)
            r.raise_for_status()
            answer = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            log_query(user_query, answer)
            return answer, "Gemini 1.5 Flash (Google)"
        except Exception as e:
            errors.append(f"Gemini error: {str(e)}")

    # 4. Try OpenRouter (Llama 3 8B Instruct Free)
    if openrouter_key:
        try:
            headers = {"Authorization": f"Bearer {openrouter_key}", "Content-Type": "application/json"}
            payload = {
                "model": "meta-llama/llama-3-8b-instruct:free",
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            }
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers)
            r.raise_for_status()
            answer = r.json()["choices"][0]["message"]["content"]
            log_query(user_query, answer)
            return answer, "Llama 3 8B (OpenRouter)"
        except Exception as e:
            errors.append(f"OpenRouter error: {str(e)}")

    if errors:
        return "⚠️ All configured AI providers failed. Details:\n\n" + "\n".join(errors), "Error"
    
    return "⚠️ No valid API keys found in secrets. Check your `.streamlit/secrets.toml` file.", "Error"


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
