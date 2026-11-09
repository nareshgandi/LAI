# Week 1 --- Session 1: PostgreSQL Adoption Lab

**Lab:** Build a PostgreSQL diagnostic assistant with
application-managed conversation context

> **This is an additional PostgreSQL adaptation**, not a lab shown in
> the Manifold session. It applies the session's concepts---LLM calls,
> state, tool boundaries and controlled execution---to a DBA scenario.

## 1. Objective

Build a small Python application that:

1.  connects to PostgreSQL using a dedicated monitoring account;
2.  collects a limited diagnostic snapshot;
3.  sends that snapshot to an LLM for explanation;
4.  retains the exchange in application memory;
5.  sends a follow-up question with previous messages included.

The LLM will explain data. It will **not** generate or execute SQL in
this lab.

## 2. Architecture

``` text
                  DBA
                   |
                   v
          Python application
            /           \
           v             v
  PostgreSQL query    Message history
           \             /
            \           /
             v         v
               LLM API
                  |
                  v
          Diagnostic explanation
                  |
                  v
            Follow-up question
                  |
                  v
       Application resends relevant
          message history to LLM
```

  -----------------------------------------------------------------------
  Session concept                     PostgreSQL adaptation
  ----------------------------------- -----------------------------------
  User goal                           Explain the PostgreSQL diagnostic
                                      snapshot

  Tool/action                         Python function that queries
                                      PostgreSQL

  Tool result                         Structured diagnostic values

  Application state                   Python list of messages

  Reasoning engine                    LLM

  Termination                         The small lab ends after the
                                      follow-up response

  Authorization                       PostgreSQL monitoring role and
                                      application boundaries
  -----------------------------------------------------------------------


## Requirements.txt — packages and why they are required

| Requirement / package | Why it is required |
|---|---|
| `langchain-openai` | Connects the Python application to an OpenAI chat model through LangChain. |
| `python-dotenv` | Loads PostgreSQL connection settings and the API key from `.env`. |
| `psycopg2-binary` | Provides the PostgreSQL DB-API driver used by Python to connect and execute the diagnostic query. |

Create `requirements.txt`:

```text
langchain-openai
python-dotenv
psycopg2-binary
```

## 3. Prerequisites

-   A reachable PostgreSQL instance.
-   Python and a virtual environment.
-   An API key for a supported model.
-   Permission to create a dedicated monitoring login.

Install:

``` bash
python -m pip install langchain-openai python-dotenv psycopg2-binary
```

## 4. Create a restricted PostgreSQL login

Run as an appropriately privileged PostgreSQL administrator:

``` sql
CREATE ROLE ai_dba_reader
    LOGIN
    PASSWORD 'replace-with-a-strong-password';

GRANT CONNECT ON DATABASE postgres TO ai_dba_reader;
GRANT pg_monitor TO ai_dba_reader;
```

`pg_monitor` is a predefined monitoring role. It provides access to a
range of monitoring information; it is not a universal read-only role
for all application data.

Use a lab password only for the lab. Do not reuse production
credentials.

## 5. Project structure

``` text
postgres_diagnostic_assistant/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── main.py
```

`.env`:

``` dotenv
OPENAI_API_KEY=replace-with-your-key

PGHOST=localhost
PGPORT=5432
PGDATABASE=postgres
PGUSER=ai_dba_reader
PGPASSWORD=replace-with-your-password
```

`.env.example`:

``` dotenv
OPENAI_API_KEY=

PGHOST=localhost
PGPORT=5432
PGDATABASE=postgres
PGUSER=ai_dba_reader
PGPASSWORD=
```

`.gitignore`:

``` gitignore
.env
.venv/
__pycache__/
*.py[cod]
```

`requirements.txt`:

``` text
langchain-openai
python-dotenv
psycopg2-binary
```

Install:

``` bash
python -m pip install -r requirements.txt
```

## 6. Implement the diagnostic snapshot and conversation

Create `main.py`:

``` python
import os

import psycopg2
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
)

load_dotenv()


def collect_database_snapshot():
    """Collect a small snapshot from the current database."""
    connection = psycopg2.connect(
        host=os.getenv("PGHOST"),
        port=os.getenv("PGPORT"),
        dbname=os.getenv("PGDATABASE"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        connect_timeout=5,
        application_name="postgres_diagnostic_learning_lab",
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    datname,
                    numbackends,
                    xact_commit,
                    xact_rollback,
                    blks_read,
                    blks_hit,
                    deadlocks
                FROM pg_stat_database
                WHERE datname = current_database()
                """
            )
            row = cursor.fetchone()

            if row is None:
                raise RuntimeError(
                    "No pg_stat_database row found for current database"
                )

            column_names = [
                "database",
                "active_backends",
                "transactions_committed",
                "transactions_rolled_back",
                "blocks_read",
                "blocks_hit",
                "deadlocks",
            ]

            return dict(zip(column_names, row))
    finally:
        connection.close()


def format_snapshot(snapshot):
    return "\n".join(
        f"{key}: {value}" for key, value in snapshot.items()
    )


def main():
    snapshot = collect_database_snapshot()

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )

    # Application-managed conversation state.
    messages = [
        SystemMessage(
            content=(
                "You are a PostgreSQL diagnostic assistant. "
                "Explain only what can reasonably be inferred from "
                "the supplied snapshot. Distinguish observations "
                "from hypotheses. Do not invent missing metrics. "
                "Do not recommend executing destructive SQL."
            )
        )
    ]

    first_question = (
        "Analyze this PostgreSQL diagnostic snapshot. "
        "Explain what each metric represents and identify "
        "which observations, if any, deserve further investigation.\n\n"
        f"{format_snapshot(snapshot)}"
    )

    messages.append(HumanMessage(content=first_question))

    first_response = llm.invoke(messages)
    print("\nFIRST RESPONSE\n")
    print(first_response.content)

    # Preserve the assistant response in application memory.
    messages.append(AIMessage(content=first_response.content))

    follow_up = input("\nAsk a follow-up question: ").strip()

    if not follow_up:
        print("No follow-up question supplied.")
        return

    messages.append(HumanMessage(content=follow_up))

    # Previous messages are supplied again with the new request.
    second_response = llm.invoke(messages)

    print("\nFOLLOW-UP RESPONSE\n")
    print(second_response.content)


if __name__ == "__main__":
    main()
```

Run:

``` bash
python main.py
```

## 7. Experiment A --- Conversation with history

After the first diagnostic response, ask:

``` text
What does blocks_hit mean in the snapshot you just analyzed?
```

The second request contains the system message, original diagnostic
question and snapshot, first assistant response, and follow-up question.

The application resends these messages to the model.

## 8. Experiment B --- Remove the previous conversation

For a controlled comparison, replace the second invocation with a fresh
message list:

``` python
fresh_messages = [
    messages[0],
    HumanMessage(content=follow_up),
]

second_response = llm.invoke(fresh_messages)
```

Ask the same follow-up question.

The model may still explain `blocks_hit` from general knowledge.
However, the specific snapshot and previous response are no longer in
the request.

This is the distinction:

-   A model can answer a general PostgreSQL question without
    conversation history.
-   It cannot reliably refer to a particular earlier diagnostic result
    unless that information is supplied.

## 9. Experiment C --- Inspect the message history

Before the second invocation, add:

``` python
for index, message in enumerate(messages):
    print(
        index,
        type(message).__name__,
        str(message.content)[:200],
    )
```

Observe how the application stores and resends messages.

In this simple implementation, memory is a Python list, not hidden
memory inside the LLM.

## 10. DBA interpretation notes

The snapshot includes counters from `pg_stat_database`:

-   `numbackends` is the number of backends connected to the database at
    the time represented by the statistics.
-   `xact_commit` and `xact_rollback` are cumulative transaction
    counters.
-   `blks_read` and `blks_hit` are cumulative block counters.
-   `deadlocks` is a cumulative deadlock counter.

Do not infer a current cache-hit ratio or a performance problem from a
single cumulative snapshot without considering measurement interval,
workload, resets and other relevant evidence.

A cache-hit ratio can be calculated as:

``` text
blks_hit / (blks_hit + blks_read)
```

but the interpretation needs context. A single ratio is not a complete
diagnosis.

## 11. Safety boundaries

This lab intentionally keeps the LLM away from database execution:

-   PostgreSQL access is limited to a monitoring login.
-   The query is fixed in application code.
-   User follow-up text is not concatenated into SQL.
-   The LLM receives diagnostic values, not database credentials.
-   The LLM does not receive a SQL execution tool.

Later sessions can introduce tool calling, explicit authorization, query
validation, audit logging and human approval.

## 12. Lab completion checklist

-   [ ] Created the monitoring role.
-   [ ] Connected from Python.
-   [ ] Retrieved the diagnostic snapshot.
-   [ ] Sent the snapshot to the LLM.
-   [ ] Asked a follow-up question with message history.
-   [ ] Repeated the question without history.
-   [ ] Compared the two requests.
-   [ ] Explained where conversation state lives.
-   [ ] Confirmed that the LLM cannot execute SQL in this lab.

## 13. What this lab demonstrates

1.  The LLM is one component of a larger application.
2.  The application retrieves and owns the relevant state.
3.  Conversation history must be included when a follow-up depends on
    earlier context.
4.  Database actions should remain under explicit application and
    database controls.
