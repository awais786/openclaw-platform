"""Plain service functions behind the MCP tools.

Kept free of any MCP dependency so they're unit-testable on their own; the MCP server
(mcp_server.py) is a thin wrapper over these.
"""
from __future__ import annotations

from .library import load_library
from .reply import draft_reply


def contact_us_reply(message: str, *, llm, library_path: str) -> dict:
    """Draft a reply grounded in the uploaded PDFs. Returns a JSON-friendly dict."""
    docs = load_library(library_path)
    if not docs:
        return {"text": "", "citations": [], "grounded": False,
                "note": "no knowledge base configured — run `openclaw upload <pdfs>`"}
    reply = draft_reply(message, docs, llm)
    return {"text": reply.text, "citations": reply.citations, "grounded": reply.grounded}


def knowledge_base(library_path: str) -> list[str]:
    """Names of the PDFs currently available to ground replies."""
    return [d.name for d in load_library(library_path)]
