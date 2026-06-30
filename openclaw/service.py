"""Plain service functions behind the MCP tools.

Free of any MCP dependency so they're unit-testable. `contact_us_reply` works against any
KnowledgeBackend (backends.py) — that's the agnostic seam; the caller picks the backend.
"""
from __future__ import annotations

from .library import load_library


def contact_us_reply(message: str, *, backend) -> dict:
    """Draft a grounded reply via the given KnowledgeBackend. Returns a JSON-friendly dict."""
    reply = backend.draft_reply(message)
    return {"text": reply.text, "citations": reply.citations, "grounded": reply.grounded}


def knowledge_base(library_path: str) -> list[str]:
    """Names of the PDFs currently available to ground replies (Files-API backend)."""
    return [d.name for d in load_library(library_path)]
