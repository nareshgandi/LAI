# Week 1 --- Session 1: Knowledge Assessment

**Topic:** Production-aware LLM foundations, agent loops, application
state and PostgreSQL adaptation

Choose one best answer for each question. The answer key is at the end;
attempt the questions first.

## Questions

### 1. What is the main difference between the simple non-agentic flow and the agentic flow described in the session?

A. An agentic system always uses a larger model.\
B. An agentic system may make multiple decisions and take multiple
actions to achieve a goal.\
C. A non-agentic system cannot use an API.\
D. An agentic system never needs application code.

### 2. Which sequence matches the mental model introduced by the instructor?

A. Train → Deploy → Fine-tune → Stop\
B. Parse → Compile → Link → Execute\
C. Observe → Think → Act → Repeat\
D. Store → Index → Vacuum → Analyze

### 3. Why can an agent loop create production risk?

A. Every loop automatically changes model weights.\
B. Repeated decisions and actions can compound errors, increase cost or
continue without reaching a goal.\
C. A loop prevents tool execution.\
D. Loops make all outputs deterministic.

### 4. An LLM proposes calling a tool to delete a database. Where should authorization and execution control be enforced?

A. Only in the natural-language system prompt.\
B. In explicit application-side policy and execution controls, with
database permissions as another boundary.\
C. By setting temperature to zero.\
D. By asking the LLM whether it is safe.

### 5. In the session's conceptual architecture, what is the reasoning engine?

A. The LLM.\
B. The PostgreSQL WAL.\
C. The Python virtual environment.\
D. The Git repository.

### 6. What does the session mean when it says the LLM API is stateless by default?

A. The model cannot answer follow-up questions.\
B. Independent requests do not automatically contain arbitrary prior
conversation messages.\
C. The model has no general knowledge.\
D. The application cannot store messages.

### 7. Where can a simple application store conversation history?

A. Only inside model weights.\
B. Only in an embedding index.\
C. In application-managed state, such as a Python list or persistent
store.\
D. In the API key.

### 8. Which is an example of a termination control?

A. Maximum iteration count.\
B. Font size.\
C. Git branch name.\
D. SQL column alias.

### 9. A diagnostic agent repeatedly invokes the same tool and never completes. Which control most directly bounds the number of steps?

A. Increasing the context window.\
B. Setting an explicit maximum-step or iteration limit.\
C. Increasing temperature.\
D. Removing application logs.

### 10. Which task should normally be handled by SQL or ordinary application code rather than an LLM?

A. Interpreting a vague natural-language request.\
B. Explaining a complex incident narrative.\
C. Counting rows in a table.\
D. Summarizing an unstructured incident report.

### 11. A Python application sends a first PostgreSQL diagnostic question and later asks, "What did you say about deadlocks?" What must it do if the model request is otherwise independent?

A. Send relevant prior messages or equivalent state again.\
B. Reinstall PostgreSQL.\
C. Change the API key.\
D. Increase the database connection count.

### 12. What is the purpose of structured logging?

A. To make the LLM more creative.\
B. To record events consistently so execution can be traced and
investigated.\
C. To store API keys in plain text.\
D. To replace authorization.

### 13. Which statement about `.gitignore` is correct?

A. It encrypts secrets.\
B. It automatically removes previously committed secrets from Git
history.\
C. It helps prevent matching untracked files from being added, but does
not untrack files already committed.\
D. It rotates exposed API keys.

### 14. Why should a PostgreSQL diagnostic lab use a dedicated monitoring account?

A. To give the LLM superuser access.\
B. To limit database privileges to what the diagnostic application
needs.\
C. To avoid using SQL.\
D. To make the model stateful.

### 15. A single `pg_stat_database` snapshot shows a high `blks_read` counter. What is the most defensible conclusion?

A. The database is definitely slow.\
B. The cache is definitely broken.\
C. It is a cumulative counter that needs interval and workload context
before drawing a performance conclusion.\
D. The database must be restarted immediately.

## Answer key and explanations

```{=html}
<details>
```
```{=html}
<summary>
```
Reveal answers and explanations
```{=html}
</summary>
```
  --------------------------------------------------------------------------
  Q                       Answer                  Explanation
  ----------------------- ----------------------- --------------------------
  1                       B                       Agentic applications can
                                                  pursue a goal through
                                                  multiple decisions and
                                                  actions.

  2                       C                       This is the
                                                  observe-think-act-repeat
                                                  mental model from the
                                                  session.

  3                       B                       Repeated decisions can
                                                  compound mistakes, consume
                                                  resources and fail to
                                                  terminate.

  4                       B                       Model proposals are not
                                                  authorization. Application
                                                  policy and database
                                                  permissions must control
                                                  execution.

  5                       A                       The instructor identifies
                                                  the LLM as the reasoning
                                                  engine.

  6                       B                       Prior messages must be
                                                  supplied or managed
                                                  through an explicit state
                                                  facility.

  7                       C                       A Python list is enough
                                                  for a simple in-process
                                                  demonstration; persistent
                                                  systems need durable
                                                  storage.

  8                       A                       An iteration limit is an
                                                  explicit termination
                                                  control.

  9                       B                       A maximum-step limit
                                                  directly bounds the loop.

  10                      C                       Counting rows is a
                                                  deterministic database
                                                  operation.

  11                      A                       The application must
                                                  provide the relevant prior
                                                  context.

  12                      B                       Structured events support
                                                  tracing, debugging and
                                                  operations.

  13                      C                       `.gitignore` does not
                                                  erase existing Git
                                                  tracking or history.

  14                      B                       Least privilege limits the
                                                  impact of application
                                                  errors or compromise.

  15                      C                       The counter is cumulative;
                                                  use deltas and workload
                                                  context to interpret it.
  --------------------------------------------------------------------------

```{=html}
</details>
```
## Self-assessment

-   **13--15 correct:** Strong grasp of this session's foundations.
    Explain the architecture without referring to the notes.
-   **10--12 correct:** Good initial understanding. Revisit missed
    questions and reproduce the relevant lab.
-   **7--9 correct:** Review agent state, tool boundaries and
    termination controls.
-   **0--6 correct:** Revisit the theory and run the original lab slowly
    before moving on.

A high score is not proof of mastery. You should also be able to explain
why the incorrect options are wrong.
