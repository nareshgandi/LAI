# Week 1 --- Session 1: Original Lab

**Theme:** Python environment setup, provider connectivity and stateless
LLM calls

> **Source boundary:** Steps and examples are based on the supplied
> Manifold transcript and screenshots. The screenshots show particular
> model identifiers; provider model availability changes, so verify the
> current identifier before running.

## Lab objectives

-   Create and activate a Python virtual environment.
-   Install LangChain provider integrations.
-   Store API keys in a local environment file.
-   Call an OpenAI model through LangChain.
-   Call a Gemini model through LangChain.
-   Inspect response content and usage metadata.
-   Observe that independent calls do not automatically include previous
    conversation messages.

## 1. Prerequisites

The instructor recommends Anaconda, VS Code or Cursor, and an OpenAI API
key or Google AI Studio API key. The instructor demonstrates Conda while
acknowledging `venv` and `uv` as alternatives.

This version uses Python's built-in `venv` to keep the commands
portable.

## 2. Create the project

``` bash
mkdir agentic_ai_session01
cd agentic_ai_session01
python -m venv .venv
```

Activate on Linux/macOS:

``` bash
source .venv/bin/activate
```

Activate on Windows Command Prompt:

``` bat
.venv\Scripts\activate.bat
```

Activate on Windows PowerShell:

``` powershell
.venv\Scripts\Activate.ps1
```

Confirm:

``` bash
python --version
python -m pip --version
```


## Requirements.txt — packages and why they are required

| Requirement / package | Why it is required |
|---|---|
| `langchain` | Provides the LangChain framework abstractions used in the session. |
| `langchain-openai` | Provides the LangChain integration for calling OpenAI chat models. |
| `langchain-google-genai` | Provides the LangChain integration for calling Google Gemini models. |
| `python-dotenv` | Loads API credentials and other configuration from the local `.env` file. |

Create `requirements.txt` with these entries:

```text
langchain
langchain-openai
langchain-google-genai
python-dotenv
```

**Note:** These are the packages required for the original connectivity examples in this session, not the entire larger bootcamp dependency list shown in the screenshots. The screenshot's larger list contains dependencies for later labs too.

## 3. Install packages

``` bash
python -m pip install --upgrade pip
python -m pip install langchain langchain-openai langchain-google-genai python-dotenv
```

Create `requirements.txt`:

``` text
langchain
langchain-openai
langchain-google-genai
python-dotenv
```

Install from it:

``` bash
python -m pip install -r requirements.txt
```

**Command correction:** The `-r` flag tells pip to read package names
from a requirements file. `pip install requirements.txt` is not the
correct command for this purpose.

The instructor's screenshots also show a broad bootcamp dependency list
containing packages for later topics, including LangGraph, FastAPI,
Redis, Celery, Pydantic, PostgreSQL integrations, document processing,
embeddings and testing. Those packages are not all required for this
first connectivity exercise.

For a reproducible course repository, pin tested package versions after
validating the environment.

## 4. Protect API keys

Create `.env`:

``` dotenv
OPENAI_API_KEY=replace-with-your-key
GOOGLE_API_KEY=replace-with-your-key
```

Create `.env.example`:

``` dotenv
OPENAI_API_KEY=
GOOGLE_API_KEY=
```

Create `.gitignore`:

``` gitignore
.env
.venv/
venv/
__pycache__/
*.py[cod]
```

Never commit real API keys. `.gitignore` does not remove a file already
tracked by Git. If a key has been exposed, revoke or rotate it. Use a
secrets manager for production deployments.

## 5. OpenAI example from the session

Create `main_openai.py`:

``` python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=1,
    max_tokens=150,
)

r1 = llm.invoke("Who is the Prime Minister of India?")
print(r1.content)

r2 = llm.invoke("What is his age?")
print(r2.content)

print(r1.usage_metadata)
```

Run:

``` bash
python main_openai.py
```

Observe:

-   The first call sends one user message.
-   The second call sends a separate user message.
-   The second call does not include `r1` or the first question.
-   The model may ask who "his" refers to.
-   `usage_metadata` can expose token usage returned by the
    integration/provider.

The exact response wording is not guaranteed. The purpose is to inspect
whether prior conversation was included, not to test factual knowledge.

**Parameter note:** The screenshot shows `temperature=1` and
`max_tokens=150`. Model integrations and provider APIs can change
parameter names or supported settings. If a current model rejects a
parameter, consult the installed integration's documentation and use its
supported equivalent.

## 6. Gemini example from the session

Create `main_gemini.py`:

``` python
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash",
)

r1 = llm.invoke("Who is the Prime Minister of India?")
print(r1.content)

r2 = llm.invoke("What is his age?")
print(r2.content)

print(r1.usage_metadata)
```

Run:

``` bash
python main_gemini.py
```

**Model identifier note:** `gemini-3.5-flash` is transcribed from the
supplied screenshot. Verify that it is currently available to your
Google AI Studio/API account. If not, replace it with a currently
supported model identifier and record the substitution.

The instructor notes that OpenAI and Gemini can phrase the second
response differently. The important observation is that neither
independent call automatically includes the earlier exchange in the code
shown.

## 7. Comparison experiment

  Run      First request                         Second request
  -------- ------------------------------------- ------------------
  OpenAI   Who is the Prime Minister of India?   What is his age?
  Gemini   Who is the Prime Minister of India?   What is his age?

Record whether the second answer asks for clarification, guesses a
referent, or is grounded in the first exchange. Record usage metadata if
available.

Do not treat one model's accidental guess as proof that the application
has memory.

## 8. Lab completion checklist

-   [ ] Python environment created and activated.
-   [ ] Required packages installed.
-   [ ] `.env` created locally.
-   [ ] `.env` excluded by `.gitignore`.
-   [ ] OpenAI API call executed, if using OpenAI.
-   [ ] Gemini API call executed, if using Gemini.
-   [ ] Response content printed.
-   [ ] Usage metadata inspected.
-   [ ] Two independent requests compared.
-   [ ] Observations recorded.

## 9. What this lab does not implement

The session introduces production concepts, but this original hands-on
exercise does not yet implement a full agent loop, tool calling,
persistent memory, structured logging, retries/fallback, explicit
iteration limits, authorization policies or production secrets
management.

This is the first LLM connectivity and statelessness exercise.


## 14. Transcript-specific lab fidelity review

The transcript's actual demonstration is narrower than the initial list of intended session deliverables.

### What is demonstrated in the recording

- Anaconda distribution and Anaconda Prompt on Windows.
- VS Code, with Cursor accepted as an alternative.
- Conda as the instructor's demonstration environment; `venv` and `uv` are acknowledged alternatives.
- A project-local Conda environment using Python 3.12.
- `.env` and `.env.example` for OpenAI and Google API keys.
- `.gitignore` to avoid adding local secrets to Git.
- OpenAI Platform API key creation and billing setup.
- Google AI Studio API key creation.
- A first OpenAI LangChain invocation.
- A second independent invocation asking “What is his age?”
- A parallel Gemini demonstration showing provider-specific wording but no automatic prior-turn context.

### Important correction to the spoken install command

The transcript's speech-to-text renders the command as `pip install requirements.txt`. The standard pip command to install packages from a requirements file is:

```bash
python -m pip install -r requirements.txt
```

### Minimum dependency table for the demonstrated calls

| Requirement / package | Why it is required |
|---|---|
| `langchain-openai` | LangChain integration for OpenAI chat models. |
| `langchain-google-genai` | LangChain integration for Gemini chat models. |
| `python-dotenv` | Loads API credentials from `.env`. |

The transcript mentions a broader shared requirements file but does not preserve its complete package list or exact versions. Do not invent the instructor's full dependency list.

### Environment setup shown in the transcript

The instructor demonstrates a project-local environment with Python 3.12:

```bash
conda create --prefix ./env python=3.12
conda activate ./env
```

On Windows, he recommends Anaconda Prompt. On macOS, he recommends Terminal. He acknowledges `venv` and `uv` as alternatives.

### `.env` and `.env.example`

Example `.env`:

```dotenv
OPENAI_API_KEY=replace_with_your_key
GOOGLE_API_KEY=replace_with_your_key
```

Example `.env.example`:

```dotenv
OPENAI_API_KEY=
GOOGLE_API_KEY=
```

Example `.gitignore`:

```gitignore
.env
env/
.venv/
__pycache__/
*.py[cod]
```

**Clarification:** `.gitignore` does not remove a file already tracked or erase a secret from Git history. Rotate any exposed key.

### OpenAI and Gemini demonstration boundary

The instructor sends “Who is the Prime Minister of India?” and then independently sends “What is his age?” The second request is not supplied with the first request's messages. He repeats this pattern with Gemini. The lesson is that independent requests do not automatically share the previous exchange.

**Not demonstrated in this transcript:** a completed customer-support agent, persistent conversation memory, structured logging implementation, latency/token instrumentation or full error handling. These were mentioned as intended session deliverables, but the supplied recording segment does not show them being built.

**Provider note:** The instructor mentions particular model names and billing amounts. These are time-sensitive and the speech-to-text model identifiers are not sufficiently reliable to prescribe. Verify current provider model availability, billing and quotas before execution.
