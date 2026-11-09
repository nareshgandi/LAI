# Week 1 --- Session 1: Production-Aware LLM Foundations

**Source:** Manifold AI Learning --- Agentic AI Enterprise Mastery, Week
1, Session 1\
**Theme:** Building your first production-aware LLM foundation

> **Source boundary:** This document follows the supplied transcript and
> screenshots. Notes marked **Technical clarification** are additional
> explanations and are not attributed to the instructor.

## 1. Why AI demos often fail to become production systems

Getting a chatbot or LangChain snippet to return an answer is relatively
easy. Engineering an application that can be operated reliably is
harder.

A production-aware application needs answers to questions such as:

-   Where is conversation memory maintained?
-   Where are execution logs?
-   What happens when an LLM call fails?
-   Is there a fallback?
-   How are latency and token usage tracked?
-   How can an operator reconstruct what happened?
-   What prevents an agent from looping indefinitely?
-   How are tool calls authorized?
-   What happens when a tool fails?

A working demonstration proves that a path can succeed once. Production
engineering asks how the system behaves across failures, unexpected
inputs, repeated execution and operational incidents.

## 2. Agentic versus non-agentic applications

### 2.1 Non-agentic, single-turn flow

The instructor describes a simple flow:

1.  The user submits an input, such as "Summarize this document."
2.  The LLM processes the input.
3.  The application returns the generated summary.

This is a useful LLM-powered application, but it does not necessarily
behave as an agent. The flow can be linear and complete after one model
response.

### 2.2 Agentic flow

The instructor gives a business-analysis example: "Analyze the Q4 sales
performance of my business."

To complete the goal, an agentic application might:

1.  Retrieve data from multiple sources.
2.  Inspect the retrieved data.
3.  Identify missing values or anomalies.
4.  Compare current data with historical data.
5.  Decide whether additional work is required.
6.  Produce a final analysis.

The user's request is one goal, but the application may perform multiple
steps and make intermediate decisions.

### 2.3 The decision loop

The instructor names the central idea as a **decision loop**:

**Observe → Think → Act → Repeat**

-   **Observe:** Read the current input, available state and results
    from previous actions.
-   **Think:** Determine what should happen next.
-   **Act:** Request or execute an action, such as calling a tool.
-   **Repeat:** Observe the result and decide whether to continue or
    finish.

The loop stops when the goal is complete, a termination condition is
reached, or execution fails.

### Mental model

``` text
                 ┌──────────────────────────────┐
                 │       Current state          │
                 │ user input + history + tools │
                 └──────────────┬───────────────┘
                                v
                       ┌────────────────┐
                       │  LLM decision  │
                       │  Think / plan  │
                       └───────┬────────┘
                               v
                    ┌──────────┴──────────┐
                    │                     │
                 Finish               Tool proposal
                    │                     │
                    v                     v
              Final response      Validate in application
                                          │
                                          v
                                    Execute tool
                                          │
                                          v
                                    Tool result
                                          │
                                          └──> Update state
                                               and repeat
```

**Technical clarification:** "Agent" is used in different ways across
the industry. The loop is a useful operational mental model, not a
universal formal definition. Some agentic systems use bounded workflows
or graph orchestration rather than an unconstrained loop.

## 3. Why the loop creates production risk

The instructor identifies risks that can occur during repeated
decision-making:

  -----------------------------------------------------------------------
  Risk                                Meaning
  ----------------------------------- -----------------------------------
  Wrong tool call                     The model proposes an unsuitable
                                      tool or arguments.

  Infinite loop                       The application continues without
                                      reaching a useful stopping point.

  Cost explosion                      Repeated model calls increase token
                                      usage and cost.

  Bad memory                          Irrelevant, stale or incorrect
                                      context affects later decisions.

  No audit trail                      Operators cannot reconstruct what
                                      happened.

  Unsafe action                       An action is executed without
                                      appropriate authorization or
                                      validation.

  Slow response                       Multiple sequential calls increase
                                      end-to-end latency.

  Hallucinated intermediate result    An incorrect intermediate answer
                                      influences later steps.

  Context poisoning                   Misleading or malicious content
                                      influences model behaviour.
  -----------------------------------------------------------------------

A wrong intermediate result can affect later decisions. The application
must validate actions and results at appropriate boundaries rather than
trusting every model-generated step.

## 4. Anatomy of an agentic system

The instructor introduces four components.

### 4.1 Reasoning engine

The reasoning engine is the LLM, such as a model from GPT, Claude or
Gemini. It reads the state supplied to it and proposes what should
happen next.

The instructor describes this part as **probabilistic** because model
outputs are not guaranteed to be identical for every invocation.

### 4.2 Memory / state

The application is responsible for maintaining and supplying relevant
information, including:

-   conversation messages;
-   tool results;
-   user context.

The model can only use context that is available to it in the request or
through a supported provider-managed state mechanism.

### 4.3 Planning / routing

This component decides what happens next:

-   Is the available information sufficient to produce a final answer?
-   Is a tool needed?
-   If so, which tool should be requested?
-   Should the workflow continue or stop?

The instructor describes this as the decision logic.

### 4.4 Tool / action execution

Tools are application functions that perform work, for example:

-   database queries;
-   API calls;
-   file operations;
-   calculations.

The model may propose a tool call, but the application controls whether
and how it is executed.

### Architecture view

``` text
                  ┌─────────────────────┐
                  │   User request      │
                  └──────────┬──────────┘
                             v
                  ┌─────────────────────┐
                  │ Application state   │
                  │ history/tool results│
                  └──────────┬──────────┘
                             v
                  ┌─────────────────────┐
                  │ Reasoning engine     │
                  │        LLM           │
                  └──────────┬──────────┘
                             v
                  ┌─────────────────────┐
                  │ Planning / routing   │
                  └──────────┬──────────┘
                             v
                  ┌─────────────────────┐
                  │ Application policy   │
                  │ validation/auth      │
                  └──────────┬──────────┘
                             v
                  ┌─────────────────────┐
                  │ Tool/action execution│
                  └──────────┬──────────┘
                             v
                  ┌─────────────────────┐
                  │ Result updates state │
                  └──────────┬──────────┘
                             └──> next loop or final answer
```

**Technical clarification:** The four components are a conceptual
decomposition. In an implementation, planning/routing may be performed
partly by the LLM and partly by application code or a framework.
Validation and authorization should remain explicit application
responsibilities.

## 5. Probabilistic proposal versus controlled execution

The instructor gives a refund example:

-   The LLM proposes issuing a \$500 refund.
-   The application checks whether the tool is allowed.
-   The application validates the amount and arguments.
-   The application executes the operation only if the checks pass.

The LLM might propose \$5,000 instead of \$500. The application must not
blindly execute that proposal.

**Core principle:** The LLM proposes; application code validates and
controls execution.

**Technical clarification:** "Deterministic" does not mean that every
tool returns the same result forever. A database query such as
`SELECT count(*) FROM pg_stat_activity` can return different values as
the database changes. The useful distinction is that the tool follows
explicit program logic and its execution can be governed and tested,
whereas LLM-generated proposals are probabilistic.

## 6. Stateless LLM calls and application-managed memory

The instructor demonstrates two separate requests:

1.  "Who is the Prime Minister of India?"
2.  "What is his age?"

When the second request is sent independently, the model may ask who
"his" refers to. The second request did not include the first exchange.

The instructor's key statement is:

**The model does not own application memory; the application owns
memory.**

A basic LLM API request should be treated as independent unless the
application supplies relevant history or uses an explicit
provider-managed state/conversation feature.

  -----------------------------------------------------------------------
  Component                           Responsibility
  ----------------------------------- -----------------------------------
  LLM inference                       Processes the context supplied for
                                      that request and generates output.

  Application                         Decides what conversation state and
                                      other context to retain and
                                      provide.

  Memory store                        May persist conversation history or
                                      other useful state.

  Agent framework                     May provide abstractions for state,
                                      messages, tools and orchestration.
  -----------------------------------------------------------------------

The instructor compares an underlying model API with user-facing
applications such as ChatGPT and Claude. Those applications can
implement conversation history and memory features around model calls.

**Technical clarification:** "Stateless" here refers to the model
inference request not automatically remembering arbitrary prior API
requests. Some providers offer conversation IDs, response chaining or
managed state. That is an explicit platform/application facility, not
evidence that a bare independent request automatically contains previous
context. KV caching is also not equivalent to durable conversational
memory.

## 7. Termination conditions and loop protection

The instructor names two examples of termination controls:

-   maximum iterations;
-   cost budget.

A maximum-step limit prevents an agent from continuing indefinitely. The
instructor suggests 5--10 iterations as an initial range depending on
use-case complexity.

This is a heuristic, not a universal production value. A production
system should select limits based on task design, latency objectives,
cost limits and risk.

Useful controls can include maximum steps, wall-clock deadline,
model-call budget, token or monetary budget, tool-specific limits, and
explicit success/failure states.

## 8. Production-readiness checklist

  -----------------------------------------------------------------------
  Control                             Why it matters
  ----------------------------------- -----------------------------------
  Error handling                      Handles failed LLM requests and
                                      tool errors.

  Structured logging                  Makes execution traceable and
                                      diagnosable.

  Loop protection                     Prevents uncontrolled repeated
                                      execution.

  Cost tracking                       Tracks token usage and API cost.

  Secrets management                  Keeps API keys out of source code
                                      and Git history.

  Graceful degradation                Provides a controlled fallback when
                                      a dependency fails.

  Input validation                    Checks incoming data and arguments.

  Timeout handling                    Prevents indefinite waiting on
                                      external calls.

  Authorization                       Prevents unauthorized tool
                                      execution.
  -----------------------------------------------------------------------

### Graceful degradation

If an LLM provider is unavailable, an application might return a clear
temporary-unavailability message, allow a controlled retry, use a
configured alternative provider if compatible, or offer a reduced
non-LLM experience.

A fallback must be designed and tested. It should not silently switch
providers if doing so changes privacy, security, model behaviour or cost
assumptions.

## 9. When to use code and when to use an LLM

The instructor's answer to "Why not code everything?" is:

-   Prefer rule-based code when the task can be expressed clearly as
    rules.
-   Use an LLM when interpreting flexible natural-language input is
    difficult to capture with practical rules.
-   After interpretation, validate the extracted result and perform the
    actual operation using application code.

  Problem                                Preferred starting point
  -------------------------------------- --------------------------------------
  Count rows                             SQL
  Calculate a ratio                      SQL or Python
  Check a fixed threshold                Application code
  Parse a well-defined field             Parser or validation library
  Interpret ambiguous natural language   LLM may help
  Execute a database operation           Controlled application/database code
  Authorize an operation                 Explicit policy and application code

**Takeaway:** Do not introduce an LLM where ordinary code is sufficient.

## 10. Technical jargon

  -----------------------------------------------------------------------
  Term                                Meaning in this session
  ----------------------------------- -----------------------------------
  Agentic system                      An application that can pursue a
                                      goal through multiple decisions and
                                      actions.

  Agent loop                          Repeated observe, think, act and
                                      evaluate cycle.

  Reasoning engine                    The LLM component proposing the
                                      next step.

  Application state                   Information the application retains
                                      and supplies to execution.

  Conversation history                Previous user and assistant
                                      messages.

  Tool calling                        A model-produced request to invoke
                                      an application tool.

  Tool execution                      Actual application-side execution
                                      of a function.

  Probabilistic                       Behaviour involving probability
                                      rather than guaranteed identical
                                      outputs.

  Deterministic logic                 Explicit program logic with defined
                                      execution rules.

  Termination condition               A condition that ends the agent
                                      run.

  Iteration limit                     Maximum permitted number of agent
                                      steps.

  Graceful degradation                A controlled reduced service or
                                      fallback during failure.

  Structured logging                  Recording events in a consistent,
                                      machine-readable structure.

  Secrets management                  Secure handling of credentials and
                                      API keys.

  Context poisoning                   Misleading or malicious content
                                      influencing the supplied context.

  Fallback                            An alternative path when the
                                      primary path fails.
  -----------------------------------------------------------------------

## 11. Session takeaways

1.  A working chatbot is not automatically a production-ready
    application.
2.  An agentic system may make multiple decisions and tool calls to
    achieve one goal.
3.  The decision loop creates risks such as wrong tool calls, infinite
    loops and cost escalation.
4.  The LLM proposes; application code validates and controls execution.
5.  Conversation state must be supplied or managed explicitly.
6.  Bound agent execution with termination conditions.
7.  Use ordinary code for deterministic tasks and LLMs where flexible
    interpretation is useful.
8.  Production systems need error handling, logs, cost controls, secrets
    management, authorization and timeouts.
