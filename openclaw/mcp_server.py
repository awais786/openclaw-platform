"""MCP server — exposes OpenClaw's contact-us reply as tools for an MCP client.

Your OpenClaw agent connects to this server (stdio) and calls `draft_contact_us_reply`
when it needs a reply grounded in the company PDFs. The agent does the reasoning; this
server just drafts and reports whether the answer was grounded.

Run:  openclaw-mcp   (needs the `mcp` extra: pip install -e ".[mcp]")
Env:  ANTHROPIC_API_KEY (or `ant auth login`); OPENCLAW_LIBRARY (default ./openclaw_library.json)
"""
from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .service import contact_us_reply, knowledge_base

_LIBRARY = os.environ.get("OPENCLAW_LIBRARY", "openclaw_library.json")
mcp = FastMCP("openclaw")

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from .llm import ClaudeLLM
        _llm = ClaudeLLM()
    return _llm


@mcp.tool()
def draft_contact_us_reply(message: str) -> dict:
    """Draft a support reply to a contact-us message, grounded ONLY in the company PDFs.

    Returns {text, citations, grounded}. If `grounded` is false, the PDFs don't cover the
    question — escalate to a human instead of sending the text.
    """
    return contact_us_reply(message, llm=_get_llm(), library_path=_LIBRARY)


@mcp.tool()
def list_knowledge_base() -> list[str]:
    """List the PDF documents currently available to ground replies."""
    return knowledge_base(_LIBRARY)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
