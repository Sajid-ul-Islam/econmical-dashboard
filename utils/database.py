"""
Database layer — Supabase (PostgreSQL).
Run SCHEMA_SQL in the Supabase SQL Editor once to create all tables.
"""

import streamlit as st
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    Client = type("Client", (object,), {})  # Dummy class
from datetime import datetime, timezone
import pandas as pd
import time
import threading

_snapshot_lock = threading.Lock()



from typing import Any

def get_secret_safely(key: str, default: Any = None) -> Any:
    """Safely fetch a secret from Streamlit secrets or SECRETS_TOML environment variable."""
    try:
        val = st.secrets[key]
        if val is not None:
            return val
    except Exception:
        pass

    import os
    if "SECRETS_TOML" in os.environ:
        try:
            import tomllib
            parsed = tomllib.loads(os.environ["SECRETS_TOML"])
            return parsed.get(key, default)
        except Exception:
            pass

    return default


@st.cache_resource
def get_supabase() -> Client | None:
    if not HAS_SUPABASE:
        if "supabase_warning_shown" not in st.session_state:
            st.error("🚨 Supabase library is missing! Database features will be disabled.", icon="🚨")
            st.session_state.supabase_warning_shown = True
        return None

    supabase_secrets = get_secret_safely("supabase")
    if not supabase_secrets:
        return None

    try:
        url = supabase_secrets.get("url")
        key = supabase_secrets.get("key")
    except AttributeError:
        return None

    if not url or not key:
        return None

    return create_client(url, key)


SCHEMA_SQL = """
-- Economic indicators time series
CREATE TABLE IF NOT EXISTS economic_data (
    id          BIGSERIAL PRIMARY KEY,
    country_code VARCHAR(3)   NOT NULL,
    country_name TEXT         NOT NULL,
    indicator    VARCHAR(50)  NOT NULL,  -- gdp, gdp_per_capita, debt_pct_gdp, gold_price
    year         INTEGER      NOT NULL,
    value        FLOAT,
    source       TEXT,
    fetched_at   TIMESTAMPTZ  DEFAULT NOW(),
    verified_at  TIMESTAMPTZ,
    UNIQUE (country_code, indicator, year)
);

-- ML predictions
CREATE TABLE IF NOT EXISTS predictions (
    id           BIGSERIAL PRIMARY KEY,
    country_code VARCHAR(3)  NOT NULL,
    indicator    VARCHAR(50) NOT NULL,
    year         INTEGER     NOT NULL,
    predicted    FLOAT       NOT NULL,
    lower_bound  FLOAT,
    upper_bound  FLOAT,
    model        TEXT        DEFAULT 'prophet',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (country_code, indicator, year, model)
);

-- Data freshness tracker
CREATE TABLE IF NOT EXISTS data_freshness (
    id           BIGSERIAL PRIMARY KEY,
    country_code VARCHAR(3)  NOT NULL,
    indicator    VARCHAR(50) NOT NULL,
    last_fetched TIMESTAMPTZ DEFAULT NOW(),
    last_verified TIMESTAMPTZ,
    status       TEXT        DEFAULT 'ok',  -- ok, stale, error
    UNIQUE (country_code, indicator)
);

-- User query log (for RAG context)
CREATE TABLE IF NOT EXISTS query_log (
    id         BIGSERIAL PRIMARY KEY,
    query      TEXT        NOT NULL,
    response   TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


LOCAL_SNAPSHOT_CSV = "data/economic_data_snapshot.csv"
LOCAL_PREDICTIONS_CSV = "data/predictions_snapshot.csv"

def save_to_local_snapshot(rows: list[dict]):
    try:
        import os
        os.makedirs("data", exist_ok=True)
        new_df = pd.DataFrame(rows)
        if new_df.empty:
            return
        
        # Ensure correct column order
        cols = ["country_code", "country_name", "indicator", "year", "value", "source", "fetched_at"]
        for c in cols:
            if c not in new_df.columns:
                new_df[c] = None
        new_df = new_df[cols]

        with _snapshot_lock:
            if os.path.exists(LOCAL_SNAPSHOT_CSV):
                try:
                    old_df = pd.read_csv(LOCAL_SNAPSHOT_CSV)
                    combined = pd.concat([old_df, new_df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["country_code", "indicator", "year"], keep="last")
                    combined.to_csv(LOCAL_SNAPSHOT_CSV, index=False)
                except Exception:
                    new_df.to_csv(LOCAL_SNAPSHOT_CSV, index=False)
            else:
                new_df.to_csv(LOCAL_SNAPSHOT_CSV, index=False)
    except Exception as e:
        print(f"Error saving to local snapshot: {e}")

def save_predictions_to_local_snapshot(rows: list[dict]):
    try:
        import os
        os.makedirs("data", exist_ok=True)
        new_df = pd.DataFrame(rows)
        if new_df.empty:
            return
        
        cols = ["country_code", "indicator", "year", "predicted", "lower_bound", "upper_bound", "model", "created_at"]
        for c in cols:
            if c not in new_df.columns:
                new_df[c] = None
        new_df = new_df[cols]

        with _snapshot_lock:
            if os.path.exists(LOCAL_PREDICTIONS_CSV):
                try:
                    old_df = pd.read_csv(LOCAL_PREDICTIONS_CSV)
                    combined = pd.concat([old_df, new_df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["country_code", "indicator", "year", "model"], keep="last")
                    combined.to_csv(LOCAL_PREDICTIONS_CSV, index=False)
                except Exception:
                    new_df.to_csv(LOCAL_PREDICTIONS_CSV, index=False)
            else:
                new_df.to_csv(LOCAL_PREDICTIONS_CSV, index=False)
    except Exception as e:
        print(f"Error saving predictions to local snapshot: {e}")

def upsert_economic_data(rows: list[dict]) -> bool:
    """Insert or update economic data rows."""
    save_to_local_snapshot(rows)
    try:
        db = get_supabase()
        if not db:
            return False
        db.table("economic_data").upsert(rows, on_conflict="country_code,indicator,year").execute()
        return True
    except Exception as e:
        st.error(f"DB write error: {e}")
        return False

def fetch_economic_data(
    country_codes: list[str] | None = None,
    indicators: list[str] | None = None,
    year_start: int = 1990,
    year_end: int = 2024,
) -> pd.DataFrame:
    """Fetch economic data from Supabase, fall back to local snapshot if offline/empty."""
    df = pd.DataFrame()
    try:
        db = get_supabase()
        if db:
            q = db.table("economic_data").select("*")
            if country_codes:
                q = q.in_("country_code", country_codes)
            if indicators:
                q = q.in_("indicator", indicators)
            q = q.gte("year", year_start).lte("year", year_end)
            result = q.execute()
            if result.data:
                df = pd.DataFrame(result.data)
    except Exception as e:
        print(f"DB read error, falling back to local snapshot: {e}")

    # Fallback to local snapshot
    if df.empty:
        import os
        if os.path.exists(LOCAL_SNAPSHOT_CSV):
            try:
                local_df = pd.read_csv(LOCAL_SNAPSHOT_CSV)
                if not local_df.empty:
                    mask = (local_df["year"] >= year_start) & (local_df["year"] <= year_end)
                    if country_codes:
                        mask = mask & (local_df["country_code"].isin(country_codes))
                    if indicators:
                        mask = mask & (local_df["indicator"].isin(indicators))
                    df = local_df[mask].copy()
            except Exception as e:
                print(f"Error reading local snapshot: {e}")
                
    return df

def fetch_predictions(
    country_codes: list[str] | None = None,
    indicators: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch predictions from Supabase, fall back to local snapshot if offline/empty."""
    df = pd.DataFrame()
    try:
        db = get_supabase()
        if db:
            q = db.table("predictions").select("*")
            if country_codes:
                q = q.in_("country_code", country_codes)
            if indicators:
                q = q.in_("indicator", indicators)
            result = q.execute()
            if result.data:
                df = pd.DataFrame(result.data)
    except Exception as e:
        print(f"Prediction read error, falling back to local snapshot: {e}")

    # Fallback to local snapshot
    if df.empty:
        import os
        if os.path.exists(LOCAL_PREDICTIONS_CSV):
            try:
                local_df = pd.read_csv(LOCAL_PREDICTIONS_CSV)
                if not local_df.empty:
                    mask = pd.Series(True, index=local_df.index)
                    if country_codes:
                        mask = mask & (local_df["country_code"].isin(country_codes))
                    if indicators:
                        mask = mask & (local_df["indicator"].isin(indicators))
                    df = local_df[mask].copy()
            except Exception as e:
                print(f"Error reading predictions local snapshot: {e}")
    return df

def upsert_predictions(rows: list[dict]) -> bool:
    """Insert or update predictions, backing up locally."""
    save_predictions_to_local_snapshot(rows)
    try:
        db = get_supabase()
        if not db:
            return False
        db.table("predictions").upsert(
            rows, on_conflict="country_code,indicator,year,model"
        ).execute()
        return True
    except Exception as e:
        st.error(f"Prediction write error: {e}")
        return False


def get_freshness(country_code: str, indicator: str) -> dict | None:
    for attempt in range(3):
        try:
            db = get_supabase()
            if not db:
                return None
            result = (
                db.table("data_freshness")
                .select("*")
                .eq("country_code", country_code)
                .eq("indicator", indicator)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            # Retry on transient Windows socket saturation errors
            if attempt < 2 and ("10035" in str(e) or "WSAEWOULDBLOCK" in str(e)):
                time.sleep(0.5 * (attempt + 1))
                continue
            st.error(f"Freshness read error: {e}")
            return None


def update_freshness(country_code: str, indicator: str, status: str = "ok"):
    for attempt in range(3):
        try:
            db = get_supabase()
            if not db:
                return
            db.table("data_freshness").upsert(
                {
                    "country_code": country_code,
                    "indicator": indicator,
                    "last_fetched": datetime.now(timezone.utc).isoformat(),
                    "status": status,
                },
                on_conflict="country_code,indicator",
            ).execute()
            return
        except Exception as e:
            if attempt < 2 and ("10035" in str(e) or "WSAEWOULDBLOCK" in str(e)):
                time.sleep(0.5 * (attempt + 1))
                continue
            st.warning(f"Freshness update error: {e}")
            return
        
def batch_update_freshness(records: list[dict]):
    if not records:
        return
    for attempt in range(3):
        try:
            db = get_supabase()
            if not db:
                return
            db.table("data_freshness").upsert(
                records,
                on_conflict="country_code,indicator",
            ).execute()
            return
        except Exception as e:
            if attempt < 2 and ("10035" in str(e) or "WSAEWOULDBLOCK" in str(e)):
                time.sleep(0.5 * (attempt + 1))
                continue
            st.warning(f"Batch freshness update error: {e}")
            return


def log_query(query: str, response: str):
    try:
        db = get_supabase()
        if not db:
            return
        db.table("query_log").insert({"query": query, "response": response}).execute()
    except Exception as e:
        st.warning(f"Query log error: {e}")


def get_recent_queries(limit: int = 100) -> pd.DataFrame:
    """Fetch recent queries to use for the semantic cache / vectorized knowledge base."""
    try:
        db = get_supabase()
        if not db:
            return pd.DataFrame()
        result = db.table("query_log").select("*").order("created_at", desc=True).limit(limit).execute()
        if result.data:
            return pd.DataFrame(result.data)
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Failed to fetch query logs: {e}")
        return pd.DataFrame()


def get_all_countries_in_db() -> list[dict]:
    """Return distinct country codes and names stored in the database."""
    try:
        db = get_supabase()
        if not db:
            return []
        result = (
            db.table("economic_data")
            .select("country_code, country_name")
            .order("country_name")
            .execute()
        )
        if result.data:
            # Deduplicate in Python — Supabase JS client doesn't expose DISTINCT
            seen = {}
            for row in result.data:
                seen[row["country_code"]] = row["country_name"]
            return [{"country_code": k, "country_name": v} for k, v in seen.items()]
        return []
    except Exception as e:
        st.error(f"Country list read error: {e}")
        return []
