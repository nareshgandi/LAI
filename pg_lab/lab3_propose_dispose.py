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
