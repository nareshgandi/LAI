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
