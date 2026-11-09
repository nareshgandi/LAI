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
