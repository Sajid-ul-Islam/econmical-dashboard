# 🤖 AI Agent Architecture (EconVision)

The EconVision AI agent acts as an expert economic analyst, answering questions by grounding every response in the live data currently loaded into the dashboard.

---

## 🧠 In-Context RAG (No Vector DB Required)

Most LLM applications that need to answer questions over custom data rely on vector databases (Pinecone, Weaviate, Milvus) and embedding models. EconVision uses a simpler and more reliable approach: **In-Context RAG**.

Because the filtered macroeconomic dataset for the selected countries is small (typically 2–15 KB of text), the entire context is serialised as a structured string and injected directly into the prompt on every call.

### What the context contains (`utils/agent.py → build_data_context`)

1. **Latest snapshot** — most recent value per country per indicator, formatted for token efficiency (`$25.46T` not `25460000000000.0`).
2. **5-year trend** — formatted as `2019: $21.4T → 2020: $20.9T → …`
3. **ML forecasts** — next 5 Prophet-predicted years, if predictions are enabled by the user.
4. **Data range tag** — confirms the historical span and projection horizon to the model.

The context is wrapped in `<economic_data>` XML tags and prepended to every user message, giving the model unambiguous grounding without any retrieval step.

---

## ⚡ Semantic Cache (Vectorised KB)

Before hitting any external API, the agent checks whether a semantically equivalent question was asked recently.

- **Method:** TF-IDF vectorisation of the last 200 queries from the `query_log` table, then cosine similarity against the new query.
- **Threshold:** 0.97 — deliberately high to avoid false cache hits between questions like "highest GDP" and "highest debt".
- **Hit label:** Responses served from cache are labelled `⚡ Semantic Cache (Vectorized KB)` in the UI.
- **Benefit:** Eliminates redundant API calls for repeated questions within a session.

---

## 🔀 Multi-Model Routing & Fallbacks

The agent is a router that tries providers in order based on which keys are configured in `.streamlit/secrets.toml`. If a provider fails or is unconfigured, it falls through to the next.

| Priority | Provider | Model | Notes |
|---|---|---|---|
| 1 | **Anthropic** | `claude-3-5-sonnet-20241022` | Primary — best reasoning |
| 2 | **Groq** | `llama-3.3-70b-versatile` | Fast open-source fallback |
| 3 | **Google Gemini** | `gemini-1.5-flash-latest` | Free tier available |
| 4 | **OpenRouter** | `meta-llama/llama-3.1-8b-instruct:free` | Zero-cost last resort |

The UI always shows which model answered the query. Fallback models display an `⚠️ Fallback Model Used` caption.

---

## 🛡️ System Prompt

The agent is governed by a strict system prompt enforcing:

- Precise citation of numbers with years — no vague claims.
- Structured answers for complex questions (sections, bullet points).
- Numbers formatted consistently (`$1.2T`, `$45K`, `3.4%`).
- Scope restriction: only answers questions related to **macroeconomics, GDP, debt, inflation, unemployment, gold, silver, financial markets, and country comparisons**. Unrelated questions are politely declined.
- Dynamic projection clause: if ML predictions are hidden by the user (toggle off), the prompt explicitly instructs the model not to forecast or mention future projections.

---

## 💬 Conversation History

The agent maintains a rolling context window of the last **8 conversation turns** (user + assistant pairs). This allows follow-up questions like "what about Germany?" to resolve correctly against prior context.

---

## 📂 Relevant Files

| File | Role |
|---|---|
| `utils/agent.py` | Core logic: cache check, context building, model routing, API calls |
| `pages/Data_Lab.py` | Streamlit chat UI (AI Agent tab) — suggested questions, chat history, context inspector |
| `utils/database.py` | `log_query()` and `get_recent_queries()` used by the semantic cache |
