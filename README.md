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

## Why a separate tool (not just OpenClaw)?

OpenClaw is a capable agent — it could read PDFs and reply on its own. This tool exists for one
reason: **control over customer-facing answers.** It answers *only* from your approved PDFs and
returns an explicit `grounded` flag, so OpenClaw can **reply when grounded and escalate (never
guess) when not** — instead of hoping a general agent stays on-script. It also keeps the knowledge
base central/reusable and pins the answer model to Claude. If you don't need that guarantee, you
don't need this — give OpenClaw the PDFs directly.

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

Add the server under `mcp.servers` in OpenClaw's config (`~/.openclaw/openclaw.json`).

### A) OpenClaw on the SAME machine — stdio (simplest)

OpenClaw launches the server as a local subprocess. Nothing is exposed to the network.

```json
{
  "mcp": {
    "servers": {
      "openclaw": {
        "command": "openclaw-mcp",
        "env": {
          "ANTHROPIC_API_KEY": "...",
          "OPENCLAW_LIBRARY": "/abs/path/openclaw_library.json"
        }
      }
    }
  }
}
```

### B) OpenClaw on ANOTHER machine — HTTP

Run the server as a network service on a host the agent can reach:

```bash
OPENCLAW_MCP_TRANSPORT=streamable-http OPENCLAW_MCP_HOST=0.0.0.0 OPENCLAW_MCP_PORT=8000 \
  OPENCLAW_MCP_TOKEN=$(openssl rand -hex 24) \
  ANTHROPIC_API_KEY=... OPENCLAW_LIBRARY=/abs/path/openclaw_library.json openclaw-mcp
```

Point the remote OpenClaw at the URL, sending the token (in `~/.openclaw/openclaw.json`):

```json
{
  "mcp": {
    "servers": {
      "openclaw": {
        "url": "http://<server-host>:8000/mcp",
        "transport": "streamable-http",
        "headers": { "Authorization": "Bearer <the-token>" }
      }
    }
  }
}
```

OpenClaw's MCP client supports `streamable-http` (what our server runs) and SSE. For a managed
token instead of a literal one in the file, OpenClaw also offers `"auth": "oauth"` + `openclaw mcp login`.

> ⚠️ The token is an app-layer gate, not transport security. Still keep this on a private
> network / VPN and put TLS in front (reverse proxy) — don't expose it open to the internet.
> Your OpenClaw MCP client must support sending an `Authorization` header; if it doesn't,
> enforce auth at a reverse proxy instead.

The agent does the reasoning and decides when to call `draft_contact_us_reply`; this server only
drafts and reports whether the answer was grounded in the PDFs.

### The OpenClaw side (Gmail → draft → human review → send)

OpenClaw owns the email: it reads the support email from Gmail, calls our tool, gets a human's
approval, and sends the reply. The glue is an OpenClaw **skill** in
[`openclaw-skill/SKILL.md`](openclaw-skill/SKILL.md) — install it into your OpenClaw. It instructs
the agent to: call `draft_contact_us_reply`, show grounded drafts to a reviewer for approval, send
on approval, and escalate (never guess) when the answer isn't grounded. No email code lives in this
package — Gmail read/send is OpenClaw's job.

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
