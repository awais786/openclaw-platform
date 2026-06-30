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

## Connect to OpenClaw (MCP)

OpenClaw (or any MCP client) calls this capability as a tool. Run it as an MCP server:

```bash
pip install -e ".[mcp]"
openclaw upload faq.pdf refunds.pdf     # build the knowledge base once
openclaw-mcp                            # starts the MCP server (stdio)
```

Tools exposed:
- `draft_contact_us_reply(message)` → `{text, citations, grounded}` (escalate when `grounded` is false)
- `list_knowledge_base()` → the PDFs available for grounding

### A) OpenClaw on the SAME machine — stdio (simplest)

OpenClaw launches the server as a local subprocess. Nothing is exposed to the network.

```json
{
  "mcpServers": {
    "openclaw": {
      "command": "openclaw-mcp",
      "env": {
        "ANTHROPIC_API_KEY": "...",
        "OPENCLAW_LIBRARY": "/abs/path/openclaw_library.json"
      }
    }
  }
}
```

### B) OpenClaw on ANOTHER machine — HTTP

Run the server as a network service on a host the agent can reach:

```bash
OPENCLAW_MCP_TRANSPORT=streamable-http OPENCLAW_MCP_HOST=0.0.0.0 OPENCLAW_MCP_PORT=8000 \
  ANTHROPIC_API_KEY=... OPENCLAW_LIBRARY=/abs/path/openclaw_library.json openclaw-mcp
```

Point the remote OpenClaw at the URL:

```json
{ "mcpServers": { "openclaw": { "url": "http://<server-host>:8000/mcp" } } }
```

> ⚠️ This is now a network service that triggers Claude calls (cost) and exposes your KB. Put it
> on a private network / VPN, firewall the port to the agent's IP, or front it with a reverse proxy
> that adds auth + TLS. Don't expose it open to the internet.

The agent does the reasoning and decides when to call `draft_contact_us_reply`; this server only
drafts and reports whether the answer was grounded in the PDFs.

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
