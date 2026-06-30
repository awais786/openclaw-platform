"""Knowledge backends — where grounding comes from. Pluggable so retrieval is agnostic.

The reply pipeline depends only on the `KnowledgeBackend` protocol. The default backend has
Claude read PDFs uploaded to the Anthropic Files API. To ground on something else (a RAG
service, a vector DB, a different vendor), implement the same protocol and pass it in — nothing
else in the pipeline changes.
"""
from __future__ import annotations

from typing import Protocol

from .library import Doc
from .reply import SYSTEM_PROMPT, Reply


class KnowledgeBackend(Protocol):
    def draft_reply(self, message: str) -> Reply:
        """Return a grounded reply for `message`, or Reply(grounded=False) to escalate."""
        ...


class FilesApiBackend:
    """Default backend: Claude reads PDFs uploaded to the Anthropic Files API (no vector DB)."""

    def __init__(self, llm, docs: list[Doc], *, max_tokens: int = 1024) -> None:
        self._llm = llm
        self._docs = docs
        self._max_tokens = max_tokens

    def draft_reply(self, message: str) -> Reply:
        if not self._docs:
            return Reply(text="", citations=[], grounded=False)
        text, citations = self._llm.reply_from_pdfs(
            system=SYSTEM_PROMPT, message=message, docs=self._docs, max_tokens=self._max_tokens
        )
        return Reply(text=text, citations=citations, grounded=bool(citations))
