# OpenClaw

AI Customer Engagement engine. **Runs standalone**; connects to a Django backend over REST when
you need persistence, business rules, approval workflow, and audit.

> Design docs: see [`docs/openclaw-plan.md`](docs/openclaw-plan.md),
> [`docs/openclaw-diagrams.md`](docs/openclaw-diagrams.md),
> [`docs/phase1-design.md`](docs/phase1-design.md).

## The idea

OpenClaw knows only **tools**. Where those tools execute is a pluggable `ToolBackend`:

```
OpenClaw (runs directly)
   │  calls tools through ToolBackend
   ▼
ToolBackend ──┬── LocalBackend   → in-memory / SQLite   (no Django; dev, demos, lightweight use)
              └── DjangoBackend  → REST to the Django app (persistence, approval, audit, RBAC)
```

Same engine — swap the backend. No rewrite to go from "running OpenClaw alone" to "OpenClaw + Django".

## Layout

```
openclaw/                 # the engine — pip-installable, standalone
  runtime/                # planner · retriever · tool executor · response generator
  tools/                  # tool schemas + ToolBackend interface
    backends/local.py     # LocalBackend (no Django)
    backends/django_http.py  # DjangoBackend (REST client)
  connectors/             # contact-us, email, reddit
  llm/                    # LLMClient (provider-agnostic)
backend_django/           # Django app implementing the tools (Postgres + pgvector)
examples/                 # run-it-directly demos
```

## Quickstart

```bash
make dev            # pip install -e ".[dev]"  (engine + pytest + ruff)
make test           # run the test suite (uses the offline EchoLLM stub)
openclaw demo       # run a sample contact-us message through the pipeline
```

Run a single message:

```bash
openclaw run --message "How do I reset my password?" --email user@example.com
```

## Use Claude (real LLM)

The engine auto-selects the provider: if the `anthropic` SDK and credentials are present it uses
**ClaudeLLM** (`claude-opus-4-8` for drafting, `claude-haiku-4-5` for classification); otherwise it
falls back to the offline **EchoLLM** stub. Configure via env (see `.env.example`):

```bash
export ANTHROPIC_API_KEY=...        # or `ant auth login`
openclaw demo
```

Wiring is one entry point:

```python
from openclaw import Engine
engine = Engine.from_settings()                 # provider + backend from env/Settings
draft = engine.handle_raw("contactus", {"id": 1, "email": "u@x.com", "message": "..."})
```

## Connect Django

Set `OPENCLAW_BACKEND=django` (+ `OPENCLAW_DJANGO_URL` / `OPENCLAW_DJANGO_TOKEN`) and the engine uses
`DjangoBackend` (REST) instead of `LocalBackend`. The tool contract is identical; only the backend
changes. Point it at the running `backend_django` service.

## Config

All settings are env-driven via `Settings.from_env()` — models, thresholds, and backend selection.
See `.env.example` for the full list.
# openclaw-platform
# openclaw-platform
