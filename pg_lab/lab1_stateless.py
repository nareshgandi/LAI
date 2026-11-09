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
