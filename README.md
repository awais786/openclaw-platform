# OpenClaw

Draft **contact-us replies** grounded in a **knowledge base**, using **Claude**.

That's the whole first use case: a customer message comes in → retrieve the relevant
knowledge → the LLM drafts a reply that answers only from that knowledge, with sources.

```
openclaw/
  kb.py      # KnowledgeBase: add() / from_dir() / search()
  llm.py     # ClaudeLLM
  reply.py   # draft_reply(message, kb, llm) -> Reply(text, citations, grounded)
  cli.py     # openclaw --message "..."
```

## Use it

```bash
make dev                  # pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...        # or `ant auth login`
openclaw --message "How do I reset my password?"
openclaw --message "..." --docs ./kb   # load .md/.txt files as the knowledge base
```

In code:

```python
from openclaw import KnowledgeBase, ClaudeLLM, draft_reply

kb = KnowledgeBase.from_dir("./kb")          # your company docs (.md/.txt)
reply = draft_reply("How do I get a refund?", kb, ClaudeLLM())
print(reply.text, reply.citations)
```

If no relevant knowledge is found, `reply.grounded` is `False` and no answer is invented —
escalate to a human.

## Dev

```bash
make test      # pytest (no API key needed — uses a fake LLM)
make lint      # ruff
```

## Design docs

- **Active spec:** [`docs/contact-us-spec.md`](docs/contact-us-spec.md) — the current build
  (contact-us reply, PDFs read by Claude via the Files API).
- Longer-term vision (multi-channel, approval workflow, Django, etc.):
  [`docs/openclaw-plan.md`](docs/openclaw-plan.md) — not the current build.
