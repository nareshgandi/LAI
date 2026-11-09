# Week 1 · Session 1 — Homework

Two short tasks, about 30–45 minutes in total. Both use the lab from `03_postgres_lab.md`.

---

## Homework 1 — Add one guard rule (≈ 20 min)

**Task:** add a 10th rule to `check_proposal()` in `lab3_propose_dispose.py`:

> Reject `terminate` if the target session's `application_name` is in a **protected applications** list, for example `{"payments-batch-critical", "pg_dump", "pg_basebackup"}`.

**Steps**

1. Add `application_name` to the `SELECT` list in `CHECK_SQL`.
2. Add a `PROTECTED_APPS` set at the top of the file.
3. Add the rule in `check_proposal()` with a clear message, e.g. `"pid 399 is protected application 'pg_dump'"`.
4. Test it **without spending API credit**: start the simulator, then in `simulate_incident.py` temporarily rename `payments-batch` to `pg_dump`, and run lab 3 with the fake model (section 9 of the lab) proposing `terminate` on that PID. Wait 30 seconds after starting the simulator, so rule 9 (transaction age) doesn't fire first.

**Done when:** the guard rejects the proposal, the log line in `agent_log.jsonl` shows your new message, and nothing was executed.

**Think about:** why is it better to protect `pg_dump` in code than to tell the LLM "never kill pg_dump" in the prompt?

<details>
<summary>Hint</summary>

The prompt is a request; the guard is a rule. The LLM can ignore or forget a prompt instruction (probabilistic). Your code cannot (deterministic). LLM proposes, code disposes.
</details>

---

## Homework 2 — Read your own audit trail (≈ 15 min)

**Task:** run lab 3 once with a real LLM (OpenAI or Gemini), then answer these four questions **using only `agent_log.jsonl`**, no scrolling back in the terminal:

| # | Question | Fill in |
|---|---|---|
| 1 | How many iterations did the agent need? | |
| 2 | Was any proposal rejected? If yes, which guard rule caught it? | |
| 3 | Total tokens used across all LLM calls? | |
| 4 | Slowest LLM call, in ms? | |

Useful commands:

```bash
jq -c 'select(.event=="dispose") | {iteration, verdict, problems}' agent_log.jsonl
jq -s '[.[] | select(.event=="llm_call") | .total_tokens] | add' agent_log.jsonl
jq -s '[.[] | select(.event=="llm_call") | .latency_ms] | max' agent_log.jsonl
```

No `jq`? Open the file in VS Code and read it; each line is one event.

**Done when:** all four cells are filled, and you can explain in two sentences what the agent did, as if writing the incident note for your team lead.

**Bonus (optional):** run it 3 times. Does the LLM always propose the same PID and action? Note the differences; this is "probabilistic" in practice, and the reason evals exist (Week 5).

---

## Bring to Session 2

- Your new guard rule (Homework 1)
- Your filled table (Homework 2)
- One question you'd like answered about memory, since Session 2 builds the messages-based conversation agent
