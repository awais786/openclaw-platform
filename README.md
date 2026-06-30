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

## Run it directly (no Django)

```bash
pip install -e .
python -m examples.run_local
```

## Connect Django

Set the backend to `DjangoBackend(base_url=..., token=...)` and point it at the running
`backend_django` service. The tool contract is identical; only the backend changes.
