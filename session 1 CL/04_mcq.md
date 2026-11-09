# Week 1 · Session 1 — Check Your Understanding

12 questions: 7 on the core concepts, 5 on the PostgreSQL lab. Answer all of them before scrolling to the key. Target: 10 / 12.

---

## Part A — Core concepts

**Q1.** What single idea best separates an agent from a plain LLM call?

- A. It uses a bigger model
- B. It runs a decision loop: observe, think, act, repeat
- C. It always calls at least one tool
- D. It has a system prompt

**Q2.** You call the OpenAI API twice: "Who is the PM of India?" then "What is his age?". The second answer is "Who are you referring to?". Why?

- A. The model's training data is too old
- B. `max_tokens` was too low
- C. The model is stateless; the second call did not include the first exchange
- D. `temperature=1` made the answer random

**Q3.** ChatGPT remembers your earlier messages. Where does that memory live?

- A. Inside the GPT model weights
- B. In the application that OpenAI built on top of the model
- C. In the KV cache, permanently
- D. In your `.env` file

**Q4.** In "LLM proposes, code disposes", which part is deterministic?

- A. The LLM choosing a tool
- B. The LLM choosing the arguments
- C. Your code validating and executing the proposed call
- D. The LLM's reasoning text

**Q5.** Which of these is a **termination condition**?

- A. A system prompt that says "be brief"
- B. Max iterations or a token/cost budget
- C. Temperature set to 0
- D. Storing keys in `.env`

**Q6.** The OpenAI model is down. Which response is **graceful degradation**?

- A. Show the user the raw `RateLimitError` stack trace
- B. Retry forever until it works
- C. Fall back to Gemini, or show "We've received your request and will follow up"
- D. Crash the service so monitoring notices

**Q7.** A task is: fetch rows → check they exist → extract fields → call a function. The instructor's advice?

- A. Always use an LLM, it's more flexible
- B. Use deterministic rules: predictable, and failures are explainable
- C. Use two LLMs and compare
- D. Use an LLM with temperature 0

---

## Part B — PostgreSQL lab

**Q8.** Why does the agent read the database as `agent_ro` and execute as a **separate** role `agent_exec`?

- A. PostgreSQL requires two roles for `pg_terminate_backend`
- B. Least privilege: the role that observes can never act, and the role that acts can't read data
- C. It makes queries faster
- D. `pg_monitor` cannot run `SELECT`

**Q9.** In the lab incident, `payments-api-1` blocks 2 sessions and `payments-batch` blocks 1. Which should be terminated, and why?

- A. `payments-api-1`, because it blocks the most sessions
- B. `payments-batch`, because it is the root blocker: it blocks others and is not waiting itself
- C. Both, to be safe
- D. `reports-job`, because it's the least important

**Q10.** The LLM proposes `pg_cancel_backend` on a session in state `idle in transaction`. Why does the guard reject it?

- A. Cancel needs superuser
- B. No query is running, so cancel does nothing; the locks stay until the transaction ends
- C. Cancel would corrupt data
- D. Cancel only works on autovacuum

**Q11.** The guard re-queries `pg_stat_activity` instead of trusting the snapshot the LLM saw. Main reason?

- A. To save tokens
- B. The snapshot may be stale and the PID may be gone or reused; the LLM may also have hallucinated it
- C. `pg_stat_activity` caches results
- D. LangChain requires it

**Q12.** In Lab 2, call 2 has **more** input tokens than call 1. What does that teach?

- A. The model got slower
- B. Memory means resending history, so every turn costs more; unbounded memory leads to cost explosion
- C. Token counting is broken
- D. The second question was longer

---
---

## Answer key

| Q | Answer | Why |
|---|---|---|
| 1 | **B** | An agent is a decision loop. Tools are optional; the loop is the defining feature. |
| 2 | **C** | Each API call starts fresh. The app must resend history. Model age (A) affects facts, not follow-ups. |
| 3 | **B** | The model owns no memory. The application stores and resends it. KV caching is a speed optimisation, not memory. |
| 4 | **C** | Proposals are probabilistic. Validation and execution are your code, so they are deterministic. |
| 5 | **B** | Iterations, cost budget and time stop the loop. Temperature controls randomness, not loop length. |
| 6 | **C** | Fallback provider or a clean message. Never a raw error, never an infinite retry. |
| 7 | **B** | If rules can express it, use rules. Save the LLM for messy natural language. |
| 8 | **B** | Separation of duties. `agent_ro` can't write; `agent_exec` can signal backends but can't read `accounts`. |
| 9 | **B** | `payments-api-1` is a victim waiting on `payments-batch`. Killing it fixes nothing. "Blocks the most" is the trap. |
| 10 | **B** | `pg_cancel_backend` interrupts a running query. An idle-in-transaction session runs nothing, so only terminate releases its locks. |
| 11 | **B** | Act on live state. Snapshots age, PIDs get reused, and LLMs invent numbers. |
| 12 | **B** | Memory is resent every call. This is why later weeks teach trimming, summaries and external memory. |

**Score guide:** 11–12 ready for Session 2 · 8–10 re-read theory sections 4 and 6 · below 8 redo Lab 3 and read the guard table.
