"""Shared helpers for the Week 1 Session 1 PostgreSQL lab."""
import json
import os
import time
import uuid
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

RUN_ID = uuid.uuid4().hex[:8]
LOG_FILE = os.getenv("AGENT_LOG", "agent_log.jsonl")


# --------------------------------------------------------------------------
# Structured logging: one JSON line per event, so 2 AM debugging is grep + jq
# --------------------------------------------------------------------------
def log_event(event, **fields):
    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "run_id": RUN_ID,
        "event": event,
        **fields,
    }
    line = json.dumps(record, default=str)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")
    print(f"    [log] {line}")


# --------------------------------------------------------------------------
# The reasoning engine (probabilistic part)
# --------------------------------------------------------------------------
def get_llm():
    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                          temperature=0, max_tokens=400, timeout=30, max_retries=2)
    if provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=os.getenv("GOOGLE_MODEL", "gemini-3.5-flash"),
                                      temperature=0, max_output_tokens=400,
                                      timeout=30, max_retries=2)
    if provider == "fake":
        # Offline mode: replays canned replies from FAKE_RESPONSES (a JSON list).
        # Lets you test the guard without spending API credit.
        from langchain_core.language_models.fake_chat_models import FakeListChatModel
        return FakeListChatModel(responses=json.loads(os.environ["FAKE_RESPONSES"]))
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def call_llm(llm, messages, step):
    """One LLM call with error handling, latency and token logging.

    Returns the AI message, or None if the call failed (caller degrades gracefully).
    """
    t0 = time.perf_counter()
    try:
        reply = llm.invoke(messages)
    except Exception as exc:  # network, auth, rate limit, timeout...
        log_event("llm_error", step=step, error_type=type(exc).__name__, error=str(exc)[:200],
                  latency_ms=round((time.perf_counter() - t0) * 1000))
        return None
    usage = getattr(reply, "usage_metadata", None) or {}
    log_event("llm_call", step=step,
              latency_ms=round((time.perf_counter() - t0) * 1000),
              input_tokens=usage.get("input_tokens"),
              output_tokens=usage.get("output_tokens"),
              total_tokens=usage.get("total_tokens"))
    return reply


# --------------------------------------------------------------------------
# Database connections and the one read-only tool (deterministic part)
# --------------------------------------------------------------------------
def agent_conn():
    """The agent's eyes: agent_ro (pg_monitor, read-only, short timeouts)."""
    return psycopg.connect(os.environ["AGENT_DSN"], row_factory=dict_row,
                           autocommit=True, application_name="dba-agent")


LOCK_TREE_SQL = """
SELECT a.pid,
       a.usename,
       a.application_name,
       a.state,
       a.wait_event_type,
       pg_blocking_pids(a.pid)                                 AS blocked_by,
       round(extract(epoch FROM now() - a.xact_start))::int    AS xact_age_s,
       round(extract(epoch FROM now() - a.state_change))::int  AS state_age_s,
       left(regexp_replace(a.query, '\\s+', ' ', 'g'), 100)    AS last_query
FROM   pg_stat_activity a
WHERE  a.datname = current_database()
  AND  a.backend_type = 'client backend'
  AND  a.pid <> pg_backend_pid()
  AND (cardinality(pg_blocking_pids(a.pid)) > 0
       OR a.pid IN (SELECT unnest(pg_blocking_pids(b.pid)) FROM pg_stat_activity b))
ORDER  BY a.xact_start NULLS LAST
"""


def lock_tree(conn):
    """Tool: every session that is blocking or blocked, oldest transaction first."""
    rows = conn.execute(LOCK_TREE_SQL).fetchall()
    log_event("tool_call", tool="lock_tree", rows=len(rows))
    return rows


def as_json(rows):
    return json.dumps(rows, indent=1, default=str)
