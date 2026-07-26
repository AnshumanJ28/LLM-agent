# From-Scratch Autonomous Agent

A tool-using ReAct agent built without LangChain, LangGraph, or CrewAI. The reasoning
loop, tool schemas, memory, evaluation harness, tracing, and sandboxed code execution
are all hand-rolled.

## Setup

1. `cp .env.example .env` and fill in `GROQ_API_KEY` (required). `TAVILY_API_KEY` is
   optional -- `web_search` falls back to a clearly labeled mock without it.
2. `pip install -r requirements.txt`
3. Build the sandbox image once, before using the `code_exec` tool:
   ```
   docker build -t sandbox_exec -f docker/Dockerfile.sandbox .
   ```

## Run locally (no Docker)

```bash
python -c "
from src.agent.loop import run_agent
from src.tools.registry import get_tools
from src.tools import calculator, web_search, vector_lookup, code_exec

result = run_agent('What is 17 * (3 + 5)?', get_tools())
print(result.final_answer)
"
```

## Run with Docker Compose

```bash
docker build -t sandbox_exec -f docker/Dockerfile.sandbox .
docker compose -f docker/docker-compose.yml up --build
```

- Agent API: `POST http://localhost:8000/run` with body `{"task": "..."}`
- Trace viewer: `http://localhost:8501`

## Run the eval suite

```bash
python -m src.eval.run_eval
```

## Run tests

```bash
pytest tests/ -v
```

## Project structure

```
agent-from-scratch/
├── src/
│   ├── agent/          # loop.py (ReAct), llm_groq.py, memory.py
│   ├── tools/           # registry.py + calculator, web_search, vector_lookup, code_exec
│   ├── eval/            # golden_set.json, judge.py, run_eval.py
│   ├── trace/           # logger.py (JSONL step logging)
│   └── guardrails/      # limits.py (step/cost budgets, sanitization)
├── api/                 # FastAPI wrapper
├── viewer/              # Streamlit trace viewer
├── docker/               # Dockerfile.app, Dockerfile.sandbox, Dockerfile.viewer, compose
├── tests/
└── .github/workflows/    # CI: pytest + eval suite
```

See `PROJECT-README.md` for the full architecture spec this was built from, including
the reasoning behind each design decision (sandboxing approach, guardrail placement,
eval design).

## Design notes worth knowing when explaining this project

- **No agent framework.** The ReAct parsing (`parse_response` in `src/agent/loop.py`)
  is a hand-written regex parser, not a library's structured-output wrapper. Malformed
  model output is corrected via a retry loop rather than crashing.
- **Sandboxing.** `code_exec` uses a sibling-container approach (Docker-out-of-Docker via
  the mounted host socket) rather than true Docker-in-Docker -- simpler, avoids
  privileged-mode/storage-driver complexity, and still gives real isolation: no network,
  non-root user, read-only filesystem, memory/CPU limits, hard timeout.
- **Guardrails are enforced in code**, checked before every model call
  (`src/guardrails/limits.py`), not just requested via the prompt.
- **Eval harness** scores against a hand-written golden set with both rule-based checks
  (right tool called? completed within budget?) and an optional LLM-as-judge pass for
  open-ended tasks.
