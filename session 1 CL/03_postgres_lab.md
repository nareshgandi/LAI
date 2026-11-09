# Week 1 · Session 1 — PostgreSQL Adaptation Lab: The Lock-Incident Agent

> **Status:** Original content. Safe to reuse in the AI for DBAs course.
> **Tested:** all scripts run against real PostgreSQL (16.15, same SQL works on 17), with an offline fake model. Real LLM wording will differ from the sample outputs.

**What Manifold taught → what this lab teaches**

| Manifold concept | Manifold example | PostgreSQL version here |
|---|---|---|
| Agent = decision loop | Analyse Q4 sales | Find the root cause of a lock pile-up |
| LLM is stateless | "Who is the PM?" → "What is his age?" | "Who is the root blocker?" → "Should I terminate it?" |
| App owns memory | Messages list (next session) | Messages list, plus watching tokens grow |
| LLM proposes, code disposes | Refund of $500 vs $5,000 | `pg_terminate_backend` validated against the live DB |
| Loop protection | Max iterations | Max iterations + token budget + DB timeouts |
| Structured logging, error handling | Announced for Session 2 | Built in: JSON log line per step, graceful fallback |
| Least privilege (Q&A) | Check user permissions | Three roles: app, agent eyes, agent hands |

---

## 1. The architecture

```mermaid
flowchart LR
    subgraph DB["PostgreSQL 17 · bankdb"]
        PSA[(pg_stat_activity<br/>pg_blocking_pids)]
        ACC[(accounts)]
    end
    SIM["simulate_incident.py<br/>role: app_user"] -->|holds row locks| ACC
    subgraph AG["Agent (Python)"]
        OBS["Observe<br/>lock_tree()"]
        LLM["Think<br/>LLM proposes JSON"]
        GRD["Dispose<br/>guard re-checks live DB"]
        HUM{"Human<br/>types 'yes'"}
        EXE["Execute<br/>pg_terminate_backend"]
        LOG[["agent_log.jsonl"]]
    end
    OBS -->|"agent_ro: pg_monitor,<br/>read-only, 5s timeout"| PSA
    OBS --> LLM --> GRD
    GRD -->|rejected: feedback| LLM
    GRD -->|passed| HUM
    HUM -->|yes| EXE
    EXE -->|"agent_exec:<br/>pg_signal_backend only"| PSA
    OBS -.-> LOG
    LLM -.-> LOG
    GRD -.-> LOG
    EXE -.-> LOG
```

**Three roles, three privilege levels.** This is the "user must not gain privileges through the agent" rule from the Q&A, made concrete.

| Role | Purpose | Can | Cannot |
|---|---|---|---|
| `app_user` | The application causing the incident | Read/write `accounts` | Signal other backends |
| `agent_ro` | The agent's **eyes** | See every session and lock (`pg_monitor`) | Write anything (`default_transaction_read_only`), wait > 1 s for a lock, run > 5 s |
| `agent_exec` | The agent's **hands** | Cancel/terminate non-superuser backends (`pg_signal_backend`) | Read table data, touch system processes or superuser sessions |

The LLM never connects to the database at all. Python code does, on its behalf.

## 2. The incident

```mermaid
flowchart TD
    B["pid A · payments-batch<br/>idle in transaction<br/>holds row id=1<br/>ROOT BLOCKER"]
    P1["pid B · payments-api-1<br/>holds row id=2<br/>waits for row id=1"]
    P2["pid C · payments-api-2<br/>queued for row id=1"]
    R["pid D · reports-job<br/>waits for row id=2"]
    B -->|blocks| P1
    P1 -->|blocks| P2
    P1 -->|blocks| R
```

This is what `pg_blocking_pids()` actually reported in testing. `payments-api-2` shows as blocked by `payments-api-1`, not by the batch job, because `payments-api-1` is ahead of it in the lock queue for row 1.

> **The trap:** `payments-api-1` blocks the **most** sessions (2), but it is a victim. The real cause, `payments-batch`, blocks only 1. A naive "kill whoever blocks the most" agent kills the wrong session. The guard must reject that.

---

## 3. Setup

### 3.1 Folder layout

```
pg_lab/
├── docker-compose.yml
├── sql/01_init.sql
├── .env.example        → copy to .env
├── .gitignore
├── requirements.txt
├── common.py           shared: logging, LLM, DB, lock_tree tool
├── simulate_incident.py
├── lab1_stateless.py
├── lab2_memory.py
└── lab3_propose_dispose.py
```

All files are also in `pg_lab.zip`, delivered with these notes.

### 3.2 Start PostgreSQL 17

`docker-compose.yml`

```yaml
services:
  pg:
    image: postgres:17
    container_name: w1s1-pg
    environment:
      POSTGRES_PASSWORD: postgres_lab_pw   # lab only
      POSTGRES_DB: bankdb
    ports:
      - "5434:5432"          # 5434 on your laptop, so it won't clash with a local PostgreSQL
    volumes:
      - ./sql:/docker-entrypoint-initdb.d:ro
```

`sql/01_init.sql` (runs automatically on first start)

```sql
-- Week 1 Session 1 PostgreSQL lab: roles and sample data.
-- Runs automatically inside bankdb on the container's first start.
-- Lab-only passwords. Never reuse them anywhere real.

-- 1. The application that will cause the incident
CREATE ROLE app_user LOGIN PASSWORD 'app_pw';

-- 2. The agent's eyes: can SEE everything, can CHANGE nothing
CREATE ROLE agent_ro LOGIN PASSWORD 'agent_ro_pw';
GRANT pg_monitor TO agent_ro;                                        -- full pg_stat_activity, pg_locks
ALTER ROLE agent_ro SET default_transaction_read_only = on;          -- no writes, ever
ALTER ROLE agent_ro SET statement_timeout = '5s';                    -- a diagnostic query never hangs
ALTER ROLE agent_ro SET lock_timeout = '1s';                         -- never queue behind the incident
ALTER ROLE agent_ro SET idle_in_transaction_session_timeout = '30s'; -- never become the incident

-- 3. The agent's hands: separate role, used ONLY after the guard and a human approve
CREATE ROLE agent_exec LOGIN PASSWORD 'agent_exec_pw';
GRANT pg_signal_backend TO agent_exec;   -- may cancel/terminate non-superuser backends; nothing else
ALTER ROLE agent_exec SET statement_timeout = '5s';

-- 4. Sample data
CREATE TABLE accounts (
    id      int PRIMARY KEY,
    owner   text          NOT NULL,
    balance numeric(12,2) NOT NULL
);
INSERT INTO accounts SELECT g, 'customer_' || g, 10000 FROM generate_series(1, 100) g;
ALTER TABLE accounts OWNER TO app_user;
```

```bash
docker compose up -d
docker compose logs pg | tail -5          # wait for "ready to accept connections"
```

> If you change `01_init.sql` later: `docker compose down -v && docker compose up -d`. Init scripts only run on an empty volume.

### 3.3 Python environment

`requirements.txt` (only what this lab needs)

```text
langchain-core
langchain-openai
langchain-google-genai
python-dotenv
pydantic
psycopg[binary]
```

```bash
conda create --prefix ./env python=3.12
conda activate ./env
pip install -r requirements.txt
cp .env.example .env      # then put your real API key in .env
```

`.env.example`

```bash
# Copy to .env and fill in ONE provider's key.
# LLM_PROVIDER: openai or google
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
GOOGLE_API_KEY=your-key
GOOGLE_MODEL=gemini-3.5-flash

# Three connections, three privilege levels (lab-only passwords)
APP_DSN=postgresql://app_user:app_pw@localhost:5434/bankdb
AGENT_DSN=postgresql://agent_ro:agent_ro_pw@localhost:5434/bankdb
EXEC_DSN=postgresql://agent_exec:agent_exec_pw@localhost:5434/bankdb

# Loop protection for lab 3
MAX_ITERATIONS=3
TOKEN_BUDGET=8000
```

`.gitignore`

```gitignore
.env
venv/
env/
__pycache__/
*.pyc
agent_log.jsonl
```

### 3.4 Verify the roles before writing any AI code

```bash
psql "postgresql://agent_ro:agent_ro_pw@localhost:5434/bankdb" \
  -c "SHOW default_transaction_read_only" \
  -c "UPDATE accounts SET balance = 0 WHERE id = 5"
```

Expected: `on`, then `ERROR: cannot execute UPDATE in a read-only transaction`. **If the update succeeds, stop and fix the role.** An agent must never get write access by accident.

---

## 4. Shared code: `common.py`

Four building blocks, matching the four-part anatomy:

| Block | Anatomy part | Production checklist item |
|---|---|---|
| `log_event()` | — | Structured logging (one JSON line per event) |
| `get_llm()` | Reasoning engine | Timeout, retries, provider fallback via env |
| `call_llm()` | Reasoning engine | Error handling, latency + token logging |
| `lock_tree()` | Tool (deterministic) | Read-only, timeouts enforced by the role |

```python
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
```

**DBA notes on `LOCK_TREE_SQL`**

- `pg_blocking_pids()` is the safe, supported way to get the blocking chain. It includes sessions *ahead in the lock queue*, which is why the trap above exists.
- `backend_type = 'client backend'` keeps autovacuum, walsender and other system processes out of what the LLM even sees.
- `pid <> pg_backend_pid()` hides the agent's own session.
- The query is truncated to 100 characters: it saves tokens and avoids sending full SQL with literal values (possible PII) to an external API.

---

## 5. Start the incident

Terminal 1, leave it running:

```bash
python simulate_incident.py
```

```python
"""Creates a realistic lock incident in bankdb and keeps it alive.

Blocking tree, as pg_blocking_pids() reports it:

    payments-batch   (idle in transaction, holds row id=1)       <- ROOT BLOCKER, blocks 1
      +-- payments-api-1  (holds row id=2, first in queue for id=1) <- blocked AND blocks 2
            +-- payments-api-2  (queued behind payments-api-1 for id=1)
            +-- reports-job     (waits for id=2)

The trap: payments-api-1 blocks the MOST sessions, but it is a victim, not the cause.

Run it in its own terminal and leave it running:  python simulate_incident.py
Stop with Ctrl+C.
"""
import os
import threading
import time

import psycopg
from dotenv import load_dotenv

load_dotenv()
DSN = os.environ["APP_DSN"]
stop = threading.Event()


def session(app_name, statements, hold=False):
    try:
        with psycopg.connect(DSN, application_name=app_name) as conn:   # autocommit off = one transaction
            for sql in statements:
                conn.execute(sql)
            if hold:
                print(f"[{app_name}] pid {conn.info.backend_pid}: got its lock, now idle in transaction")
                while not stop.is_set():
                    time.sleep(1)
                conn.rollback()
            else:
                conn.commit()
                print(f"[{app_name}] finished: lock was released")
    except psycopg.OperationalError as exc:
        print(f"[{app_name}] connection ended: {str(exc).strip()[:80]}")


def start(app_name, statements, hold=False):
    t = threading.Thread(target=session, args=(app_name, statements, hold), daemon=True)
    t.start()
    time.sleep(1)  # keep the order deterministic


if __name__ == "__main__":
    start("payments-batch", ["UPDATE accounts SET balance = balance - 500 WHERE id = 1"], hold=True)
    start("payments-api-1", ["UPDATE accounts SET balance = balance + 10 WHERE id = 2",
                             "UPDATE accounts SET balance = balance + 10 WHERE id = 1"])
    start("payments-api-2", ["UPDATE accounts SET balance = balance + 20 WHERE id = 1"])
    start("reports-job",    ["UPDATE accounts SET balance = balance WHERE id = 2"])
    print("\nIncident running. Leave this terminal open; run the labs in another one. Ctrl+C to stop.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop.set()
        time.sleep(1.5)
        print("Simulator stopped.")
```

Check it the DBA way first:

```sql
SELECT pid, application_name, state, pg_blocking_pids(pid) AS blocked_by
FROM pg_stat_activity
WHERE datname = 'bankdb' AND backend_type = 'client backend';
```

---

## 6. Lab 1 — Prove the LLM is stateless

Terminal 2: `python lab1_stateless.py`

```python
"""Lab 1: prove the LLM is stateless, on a real lock incident.

Same experiment as the PM-of-India demo, but with a question a DBA would ask.
"""
from common import agent_conn, as_json, call_llm, get_llm, lock_tree

llm = get_llm()
with agent_conn() as conn:
    snapshot = lock_tree(conn)                      # tool call: deterministic

if not snapshot:
    raise SystemExit("No blocking found. Is simulate_incident.py running?")

q1 = f"""You are helping a PostgreSQL DBA during an incident.
Lock snapshot from pg_stat_activity (JSON):
{as_json(snapshot)}

Which PID is the root blocker, and what is it doing? Answer in 3 short lines."""

print("\n=== Q1: snapshot + question ===")
r1 = call_llm(llm, q1, step="q1")
print(r1.content if r1 else "LLM unavailable")

q2 = "Should I terminate it? Answer yes or no, with one reason."

print("\n=== Q2: follow-up, sent on its own ===")
r2 = call_llm(llm, q2, step="q2")
print(r2.content if r2 else "LLM unavailable")

print("\nThe model has no idea what 'it' is. Each call starts from zero: the LLM is stateless.")
```

**Expected:** Q1 gets a sensible answer naming the batch job's PID. Q2 ("Should I terminate it?") gets a confused reply: the model asks which session or what "it" means, or gives generic advice. Same lesson as the PM-of-India demo, on a problem every DBA recognises.

**Look at the log lines** printed before each answer: `latency_ms`, `input_tokens`, `output_tokens`. Q2 has very few input tokens because it was sent alone.

---

## 7. Lab 2 — The application owns memory

`python lab2_memory.py`

```python
"""Lab 2: fix the amnesia. The application owns memory and resends it.

Memory here is just a Python list of messages, sent in full on every call.
Watch input_tokens in the log: memory is not free.
"""
from langchain_core.messages import HumanMessage, SystemMessage

from common import agent_conn, as_json, call_llm, get_llm, lock_tree

llm = get_llm()
with agent_conn() as conn:
    snapshot = lock_tree(conn)

if not snapshot:
    raise SystemExit("No blocking found. Is simulate_incident.py running?")

messages = [
    SystemMessage("You are helping a PostgreSQL DBA during an incident. Be brief and precise."),
    HumanMessage(f"Lock snapshot from pg_stat_activity (JSON):\n{as_json(snapshot)}\n\n"
                 "Which PID is the root blocker, and what is it doing? Answer in 3 short lines."),
]

print("\n=== Q1 ===")
r1 = call_llm(llm, messages, step="q1")
if r1 is None:
    raise SystemExit("LLM unavailable")
print(r1.content)
messages.append(r1)                                   # <- the memory: keep the answer

messages.append(HumanMessage("Should I terminate it? Answer yes or no, with one reason."))

print("\n=== Q2: same question as lab 1, but history is resent ===")
r2 = call_llm(llm, messages, step="q2")
print(r2.content if r2 else "LLM unavailable")

print(f"\nMessages sent on call 2: {len(messages)}. Compare input_tokens of q1 vs q2 in the log above.")
```

**Expected:** Q2 now answers about the correct PID.

**The cost lesson:** compare `input_tokens` for q1 and q2. Call 2 resends the whole snapshot plus the first answer, so it costs *more* than call 1. Memory is never free. In a 20-step incident, naive memory means every call carries all previous snapshots, which is the "cost explosion" risk. Later weeks fix this with context engineering (summaries, trimming, external memory in PostgreSQL).

---

## 8. Lab 3 — LLM proposes, code disposes

`python lab3_propose_dispose.py`

```mermaid
flowchart TD
    S([start]) --> BUD{"iteration ≤ MAX<br/>and tokens under budget?"}
    BUD -->|no| ESC([Stop: escalate to on-call DBA])
    BUD -->|yes| OB[Observe: lock_tree]
    OB --> NB{blocking?}
    NB -->|no| OK([Done: nothing to do])
    NB -->|yes| TH[Think: LLM returns JSON proposal]
    TH --> ERR{LLM call ok?}
    ERR -->|no| FB([Fallback: manual runbook])
    ERR -->|yes| G{Guard on LIVE DB}
    G -->|rejected| FBK[Send reasons back to LLM] --> BUD
    G -->|passed| H{Human types 'yes'?}
    H -->|no| AB([Abort, nothing executed])
    H -->|yes| EX[Execute with agent_exec] --> LG([Logged and done])
```

```python
"""Lab 3: LLM proposes, code disposes, inside a bounded agent loop.

observe (lock_tree) -> think (LLM proposes JSON) -> dispose (guard checks live DB)
-> human approves -> execute with a separate role. Max iterations + token budget stop the loop.
"""
import json
import os
from typing import Literal, Optional

import psycopg
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from common import agent_conn, as_json, call_llm, get_llm, lock_tree, log_event

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))
TOKEN_BUDGET = int(os.getenv("TOKEN_BUDGET", "8000"))
MIN_XACT_AGE_S = 30
PROTECTED_USERS = {"postgres", "replicator", "agent_ro", "agent_exec"}

SYSTEM_PROMPT = """You are a PostgreSQL incident assistant. You may only PROPOSE one action.
A program will check your proposal against the live database and a human must approve it.

Allowed actions:
- "cancel":    pg_cancel_backend(pid). Stops the running query, keeps the session.
- "terminate": pg_terminate_backend(pid). Ends the session and rolls back its transaction.
- "none":      no action is safe or needed.

Target the ROOT blocker: a session that blocks others but is not itself waiting on a lock.
Reply with ONLY a JSON object, no markdown:
{"action": "cancel|terminate|none", "pid": <integer or null>, "reason": "<one sentence>"}"""


class Proposal(BaseModel):
    """The contract. Anything the LLM says that doesn't fit this is rejected."""
    action: Literal["cancel", "terminate", "none"]
    pid: Optional[int] = None
    reason: str = Field(max_length=500)


def parse_proposal(text):
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return Proposal.model_validate(json.loads(cleaned)), None
    except (json.JSONDecodeError, ValidationError) as exc:
        return None, f"reply is not a valid proposal: {str(exc).splitlines()[0][:150]}"


CHECK_SQL = """
SELECT a.pid, a.usename, a.backend_type, a.state, coalesce(r.rolsuper, false) AS rolsuper,
       round(extract(epoch FROM now() - a.xact_start))::int AS xact_age_s,
       cardinality(pg_blocking_pids(a.pid))                 AS waiting_on,
       (SELECT count(*) FROM pg_stat_activity b
         WHERE a.pid = ANY (pg_blocking_pids(b.pid)))       AS blocking
FROM   pg_stat_activity a
LEFT   JOIN pg_roles r ON r.rolname = a.usename
WHERE  a.pid = %s AND a.datname = current_database()
"""


def check_proposal(conn, p):
    """Deterministic guard. Re-reads the LIVE database; never trusts the LLM's view."""
    if p.action == "none":
        return []
    if p.pid is None:
        return ["a pid is required for cancel/terminate"]
    row = conn.execute(CHECK_SQL, (p.pid,)).fetchone()
    if row is None:
        return [f"pid {p.pid} does not exist in this database (hallucinated or already gone)"]

    problems = []
    if row["backend_type"] != "client backend":
        problems.append(f"pid {p.pid} is a '{row['backend_type']}', not a client backend; never signal system processes")
    if row["rolsuper"] or row["usename"] in PROTECTED_USERS:
        problems.append(f"pid {p.pid} belongs to protected role '{row['usename']}'")
    if row["blocking"] == 0:
        problems.append(f"pid {p.pid} is not blocking anyone")
    if row["waiting_on"] > 0:
        problems.append(f"pid {p.pid} is itself waiting on a lock, so it is not the root blocker")
    if p.action == "cancel" and (row["state"] or "").startswith("idle in transaction"):
        problems.append(f"pid {p.pid} is idle in transaction: cancel does nothing (no query is running); it holds locks until its transaction ends")
    if p.action == "terminate" and (row["xact_age_s"] or 0) < MIN_XACT_AGE_S:
        problems.append(f"transaction is only {row['xact_age_s']}s old; wait at least {MIN_XACT_AGE_S}s before terminating")
    return problems


def human_approves(p):
    print(f"\n  PROPOSED: {p.action} pid {p.pid}\n  REASON:   {p.reason}")
    return input("  Type 'yes' to execute, anything else to abort: ").strip().lower() == "yes"


def execute(p):
    fn = {"cancel": "pg_cancel_backend", "terminate": "pg_terminate_backend"}[p.action]  # fixed map, never LLM text
    with psycopg.connect(os.environ["EXEC_DSN"], autocommit=True, application_name="dba-agent-exec") as conn:
        return conn.execute(f"SELECT {fn}(%s)", (p.pid,)).fetchone()[0]


def run():
    llm = get_llm()
    messages = [SystemMessage(SYSTEM_PROMPT)]
    tokens_used, feedback = 0, ""

    with agent_conn() as conn:
        for i in range(1, MAX_ITERATIONS + 1):
            if tokens_used >= TOKEN_BUDGET:
                log_event("terminated", reason="token_budget", tokens_used=tokens_used)
                print("\nStopped: token budget used up. Escalate to the on-call DBA.")
                return

            # OBSERVE
            snapshot = lock_tree(conn)
            if not snapshot:
                log_event("done", reason="no_blocking")
                print("\nNo blocking sessions. Nothing to do.")
                return

            # THINK
            messages.append(HumanMessage(f"{feedback}Iteration {i}. Current lock snapshot:\n{as_json(snapshot)}"))
            reply = call_llm(llm, messages, step=f"think_{i}")
            if reply is None:
                print("\nLLM unavailable. Fall back to the manual runbook (run the lock tree query yourself).")
                return
            messages.append(reply)
            tokens_used += (getattr(reply, "usage_metadata", None) or {}).get("total_tokens", 0)

            # DISPOSE
            proposal, error = parse_proposal(reply.content)
            problems = [error] if error else check_proposal(conn, proposal)
            log_event("dispose", iteration=i,
                      proposal=proposal.model_dump() if proposal else reply.content[:200],
                      verdict="rejected" if problems else "passed", problems=problems)

            if problems:
                print(f"\n  Iteration {i}: proposal REJECTED")
                for prob in problems:
                    print(f"   - {prob}")
                feedback = "Your previous proposal was REJECTED by the safety check:\n- " + "\n- ".join(problems) + "\n\n"
                continue

            if proposal.action == "none":
                log_event("done", reason="llm_proposed_none")
                print(f"\nNo action proposed: {proposal.reason}")
                return

            # HUMAN IN THE LOOP, then EXECUTE
            approved = human_approves(proposal)
            log_event("approval", pid=proposal.pid, action=proposal.action, approved=approved)
            if not approved:
                print("Not approved. Nothing executed.")
                return
            ok = execute(proposal)
            log_event("executed", pid=proposal.pid, action=proposal.action, result=ok)
            print(f"\n{proposal.action} pid {proposal.pid}: {'done' if ok else 'failed'}")
            return

    log_event("terminated", reason="max_iterations", iterations=MAX_ITERATIONS)
    print(f"\nStopped after {MAX_ITERATIONS} iterations without a safe proposal. Escalate to the on-call DBA.")


if __name__ == "__main__":
    run()
```

### The guard, rule by rule

| # | Rule | Catches | Why a DBA cares |
|---|---|---|---|
| 1 | JSON must match `Proposal` | Chatty or malformed output | Never parse free text into an action |
| 2 | Action must be `cancel`, `terminate` or `none` | Invented actions like `vacuum` | Allowlist, not blocklist |
| 3 | PID must exist now in this DB | Hallucinated or stale PIDs | PIDs get reused; snapshots go stale |
| 4 | Must be a `client backend` | walsender, autovacuum, checkpointer | Killing a walsender breaks replication |
| 5 | Not superuser or protected role | `postgres`, replication user, the agent itself | Never let the agent touch admin or its own sessions |
| 6 | Must be blocking someone | Random targets | No victim, no action |
| 7 | Must **not** be waiting itself | The trap: `payments-api-1` | Killing a victim fixes nothing |
| 8 | `cancel` not allowed on `idle in transaction` | A cancel that does nothing | No query is running; the locks stay until the transaction ends |
| 9 | Transaction ≥ 30 s old for terminate | Killing a normal short transaction | Give real work time to finish |

Rule 8 is DBA knowledge most AI engineers don't have. That gap is exactly where your course adds value.

### What the test run showed (offline fake model, real PostgreSQL)

PIDs 399 and 401 were the root blocker and the trap in the test run; yours will differ.

Fed deliberately bad proposals, the guard rejected each one with a precise reason:

```text
Iteration 1: proposal REJECTED
 - reply is not a valid proposal: Expecting value: line 1 column 1 (char 0)
Iteration 2: proposal REJECTED
 - pid 401 is itself waiting on a lock, so it is not the root blocker
Stopped after 2 iterations without a safe proposal. Escalate to the on-call DBA.
```

```text
Iteration 1: proposal REJECTED
 - pid 399 is idle in transaction: cancel does nothing (no query is running); it holds locks until its transaction ends
Iteration 2: proposal REJECTED
 - pid 99999 does not exist in this database (hallucinated or already gone)
  PROPOSED: terminate pid 399
  REASON:   Root blocker idle in transaction holding row 1
Not approved. Nothing executed.
```

And when approved:

```text
terminate pid 399: done
[payments-api-1] finished: lock was released
[payments-api-2] finished: lock was released
[reports-job] finished: lock was released
```

Extra checks done during testing:

| Test | Result |
|---|---|
| `UPDATE` as `agent_ro` | `ERROR: cannot execute UPDATE in a read-only transaction` |
| `pg_terminate_backend(<checkpointer pid>)` as `agent_exec` | Returns `false` with a warning that the PID is not a PostgreSQL backend process: system processes can't be signalled |
| `SELECT … FROM accounts` as `agent_exec` | `ERROR: permission denied for table accounts` |
| Lock tree after terminate | Empty: all three waiters completed |

Defence in depth: even if the guard had a bug, PostgreSQL's own role limits stop the worst actions.

### Read the audit trail

Every step is in `agent_log.jsonl`, one JSON object per line:

```json
{"ts": "...", "run_id": "d8112213", "event": "dispose", "iteration": 1,
 "proposal": {"action": "terminate", "pid": 399, "reason": "Root blocker idle in transaction holding row 1"},
 "verdict": "passed", "problems": []}
{"ts": "...", "run_id": "d8112213", "event": "approval", "pid": 399, "action": "terminate", "approved": true}
{"ts": "...", "run_id": "d8112213", "event": "executed", "pid": 399, "action": "terminate", "result": true}
```

```bash
# What did the agent do in its last run?
tail -20 agent_log.jsonl | jq -c '{event, iteration, verdict, pid, latency_ms, total_tokens}'
```

That answers the 2 AM question: who proposed what, why it was accepted or rejected, who approved it, and what it cost.

---

## 9. Optional: test the guard without spending API credit

`get_llm()` has a `fake` provider that replays canned replies. Use it to try your own bad proposals. Replace `399` with the real root-blocker PID from your simulator output:

```bash
LLM_PROVIDER=fake MAX_ITERATIONS=2 \
FAKE_RESPONSES='["{\"action\":\"cancel\",\"pid\":399,\"reason\":\"root\"}", "{\"action\":\"terminate\",\"pid\":1,\"reason\":\"x\"}"]' \
python lab3_propose_dispose.py
```

On Windows, set the variables in `.env` instead of on the command line.

---

## 10. Clean up

```bash
# Terminal 1: Ctrl+C to stop the simulator
docker compose down -v      # removes the container and its data
```

---

## 11. Mapping to the production checklist

| Checklist item | Where it lives in this lab |
|---|---|
| Error handling | `call_llm()` returns `None` on failure; lab 3 falls back to the manual runbook |
| Structured logging | `log_event()` → `agent_log.jsonl` |
| Loop protection | `MAX_ITERATIONS` |
| Cost tracking | `TOKEN_BUDGET` + tokens logged per call |
| Secrets management | `.env` + `.gitignore`; lab-only passwords |
| Graceful degradation | "Escalate to the on-call DBA" instead of a crash |
| Input validation | `Proposal` model + guard on live data |
| Timeout handling | LLM `timeout=30`; `statement_timeout` and `lock_timeout` on `agent_ro` |
