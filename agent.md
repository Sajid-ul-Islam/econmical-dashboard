# 🤖 AI Agent Architecture (EconVision)

The EconVision AI agent acts as an expert economic analyst, answering user questions by grounding its responses in the live data loaded into the dashboard.

## 🧠 In-Context RAG (Retrieval-Augmented Generation)

Unlike many LLM applications that rely on complex Vector Databases (like Pinecone or Milvus) and embedding models, this dashboard leverages **In-Context RAG**. 

Because the filtered macroeconomic data for selected countries is relatively small (a few kilobytes of text), we can serialize the Pandas DataFrames directly into a highly structured, human-readable string and inject it directly into the LLM's prompt window.

### Context Building (`utils/agent.py`)
1. **Latest Snapshots:** Extracts the most recent data point for the selected countries/indicators.
2. **Recent Trends:** Formats the last 5 years of historical data into a flow (e.g., `2019: $21.38T → 2020: ...`).
3. **Forecasts:** Formats the next 5 years of Prophet ML predictions.
4. **Token Efficiency:** Uses formatting helpers (like converting `25460000000000.0` to `$25.46T`) to drastically reduce token consumption and prevent LLM hallucinations.

## 🔀 Multi-Model Routing & Fallbacks

To ensure maximum uptime and flexibility, the agent acts as a router that sequentially attempts to use different AI providers based on the keys available in `.streamlit/secrets.toml`.

1. **Primary:** Anthropic (`claude-3-5-sonnet-20241022`)
2. **Fallback 1:** Groq (`llama3-70b-8192`) - Extremely fast inference.
3. **Fallback 2:** Google Gemini (`gemini-1.5-flash`)
4. **Fallback 3:** OpenRouter (`meta-llama/llama-3-8b-instruct:free`)

If one service fails or is unconfigured, it gracefully degrades to the next available option, reporting back which model successfully answered the prompt in the UI.

## 🛡️ System Prompt Constraints

The agent is governed by a strict system prompt that enforces:
- Precise citation of numbers and years.
- Emphasis on trends, anomalies, and comparative insights.
- Strict boundary adherence (it will politely refuse to answer questions unrelated to macroeconomics, finance, or development).

## 📂 Relevant Files
- `utils/agent.py`: Core routing, prompt building, and API calls.
- `pages/AI_Agent.py`: The Streamlit chat UI.