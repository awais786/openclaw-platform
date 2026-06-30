# OpenClaw

Draft **contact-us replies** grounded in a **knowledge base**, using **Claude**.

The whole first use case: **upload a handful of company PDFs once**, then for each customer
message Claude **reads the PDFs directly** and drafts a reply that answers only from them, with
citations. No vector DB, no retrieval index.

```
openclaw/
  library.py  # the KB = uploaded PDFs: Doc(file_id, name) + upload_pdfs / save / load
  llm.py      # ClaudeLLM: upload_pdf() + reply_from_pdfs()
  reply.py    # draft_reply(message, docs, llm) -> Reply(text, citations, grounded)
  cli.py      # openclaw upload ... | openclaw reply --message "..."
```

## Use it

```bash
make dev                              # pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...          # or `ant auth login`

openclaw upload faq.pdf refunds.pdf   # upload once → saves openclaw_library.json
openclaw reply --message "How do refunds work?"
```

In code:

```python
from openclaw import ClaudeLLM, upload_pdfs, save_library, load_library, draft_reply

llm = ClaudeLLM()
docs = upload_pdfs(["faq.pdf", "refunds.pdf"], llm)   # run once when docs change
save_library(docs, "openclaw_library.json")

reply = draft_reply("How do I get a refund?", load_library("openclaw_library.json"), llm)
print(reply.text, reply.citations)
```

If Claude cites nothing (the PDFs don't cover the question), `reply.grounded` is `False` and no
answer is invented — escalate to a human.

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
