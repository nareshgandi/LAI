# Week 1 --- Session 1: Homework

**Estimated time:** 20--30 minutes\
**Goal:** Reinforce application-managed state and the boundary between
an LLM proposal and controlled execution.

## Homework 1 --- Explain statelessness in your own words

**Estimated time:** 10 minutes

Write a short explanation (150--250 words) answering:

1.  Why did the second independent LLM call fail to resolve "his"
    reliably in the original demonstration?
2.  What did the Python application need to send to preserve the
    conversation?
3.  Is a Python list the same thing as durable, persistent memory?
4.  What would you change if the application had to preserve
    conversations across process restarts?

Use one PostgreSQL DBA example in your explanation.

**Deliverable:** A short Markdown answer saved as
`homework-01-statelessness.md`.

## Homework 2 --- Extend the PostgreSQL diagnostic snapshot

**Estimated time:** 10--20 minutes

Modify the PostgreSQL adoption lab to collect one additional metric:

``` sql
SELECT
    datname,
    deadlocks,
    temp_files,
    temp_bytes
FROM pg_stat_database
WHERE datname = current_database();
```

Then:

1.  Include the new fields in the diagnostic snapshot.
2.  Include them in the text sent to the LLM.
3.  Ask a follow-up question about `temp_bytes`.
4.  Repeat the follow-up without prior conversation history.
5.  Record what changed.

**Deliverable:** Updated `main.py` and a short observation (3--5
sentences).

## Submission checklist

-   [ ] I can explain why independent LLM requests do not automatically
    share conversation history.
-   [ ] I can identify where the application stores messages in the lab.
-   [ ] I added the PostgreSQL metrics.
-   [ ] I compared a follow-up with and without history.
-   [ ] I recorded my observations.

## Reflection question

If the Python process restarts, what happens to the `messages` list?

What would you use to preserve the conversation across restarts, and
what additional information would you need to identify the correct
conversation for each user?

Do not build a full persistence layer yet. The purpose is to identify
the next engineering problem.


## Homework 3 — Security boundary for a DBA action

**Estimated time:** 10 minutes

Scenario: A DBA asks an AI assistant to terminate a PostgreSQL backend.

Write a short design note answering:

1. What may the LLM interpret or propose?
2. What policy and user-permission checks must the application perform?
3. How should PostgreSQL privileges constrain the action?
4. Would you require human approval? Explain when and why.
5. What should be logged for later audit?

Do not implement or execute a backend-termination tool. This is a design exercise based on the instructor's security Q&A.

**Deliverable:** `homework-03-dba-tool-boundary.md`

## Homework 4 — Classify failure handling

**Estimated time:** 5 minutes

For each scenario, identify whether it is error handling, retry, graceful degradation or provider fallback:

- The UI says the assistant is temporarily unavailable.
- The application retries a transient timeout once.
- The system switches to a configured alternative model provider.
- The application offers a limited static status response while the model is unavailable.

**Deliverable:** Four classifications with one-sentence explanations.

Do not treat provider fallback as automatically safe; note one compatibility, privacy, security or cost concern.
