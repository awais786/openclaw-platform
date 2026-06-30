"""Engine — the one obvious entry point for wiring OpenClaw.

    from openclaw import Engine
    engine = Engine.from_settings()          # auto-selects provider + backend
    draft = engine.handle_raw("contactus", {"id": 1, "email": "...", "message": "..."})

Auto-selection:
  - LLM:     ClaudeLLM if the `anthropic` SDK + credentials are available, else EchoLLM.
  - Backend: LocalBackend (default) or DjangoBackend when settings.backend == "django".
"""
from __future__ import annotations

import difflib
import logging
import os

from .config import Settings
from .connectors.base import Connector
from .connectors.contactus import ContactUsConnector
from .llm.client import EchoLLM, LLMClient
from .runtime.pipeline import Pipeline
from .tools.backend import ToolBackend
from .tools.backends.local import LocalBackend
from .tools.schemas import Draft, KBChunk, ReviewResult

log = logging.getLogger("openclaw")

_CONNECTORS: dict[str, Connector] = {
    "contactus": ContactUsConnector(),
}


def _unified_diff(old: str, new: str) -> str:
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile="draft", tofile="final",
    ))


def _select_llm(settings: Settings) -> LLMClient:
    """ClaudeLLM when usable; otherwise the offline EchoLLM stub."""
    has_creds = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    try:
        import anthropic  # noqa: F401
    except ImportError:
        log.info("anthropic SDK not installed — using EchoLLM stub")
        return EchoLLM()
    if not has_creds:
        log.info("no Anthropic credentials in env — using EchoLLM stub")
        return EchoLLM()
    from .llm.claude import ClaudeLLM
    return ClaudeLLM(default_model=settings.draft_model)


def _select_backend(settings: Settings, kb: list[KBChunk] | None) -> ToolBackend:
    if settings.backend == "django":
        from .tools.backends.django_http import DjangoBackend
        return DjangoBackend(base_url=settings.django_base_url, token=settings.django_token)
    return LocalBackend(kb=kb)


class Engine:
    def __init__(self, backend: ToolBackend, llm: LLMClient, settings: Settings) -> None:
        self.settings = settings
        self.backend = backend
        self.llm = llm
        self.pipeline = Pipeline(backend, llm, settings)

    @classmethod
    def from_settings(
        cls, settings: Settings | None = None, *, kb: list[KBChunk] | None = None
    ) -> Engine:
        settings = settings or Settings.from_env()
        backend = _select_backend(settings, kb)
        llm = _select_llm(settings)
        return cls(backend, llm, settings)

    def handle_raw(self, channel: str, raw: dict) -> Draft:
        connector = _CONNECTORS.get(channel)
        if connector is None:
            raise ValueError(f"no connector registered for channel '{channel}'")
        return self.pipeline.handle(connector.normalize(raw))

    # ----- human approval loop -----
    def pending(self) -> list[dict]:
        """Drafts awaiting review."""
        return self.backend.list_pending_drafts()

    def approve(
        self, draft_id: str, *, reviewer: str, edited_text: str | None = None
    ) -> ReviewResult:
        """Approve (optionally with edits) and publish through the gated Tool Executor."""
        rec = self._pending_or_raise(draft_id)
        text = rec["text"] if edited_text is None else edited_text
        edited = edited_text is not None and edited_text != rec["text"]
        diff = _unified_diff(rec["text"], text) if edited else ""

        decision, published = self.pipeline.exec.publish_reply(
            rec["thread_key"], text, channel=rec["channel"], intent=rec["intent"],
            idempotency_key=f"approve:{draft_id}", approved_by=reviewer,
        )
        status = "edited" if edited else "approved"
        self.backend.resolve_draft(draft_id, status=status, final_text=text, edit_diff=diff)
        return ReviewResult(draft_id=draft_id, status=status,
                            published=published is not None, edit_diff=diff)

    def reject(self, draft_id: str, *, reviewer: str, reason: str) -> ReviewResult:
        """Reject with a reason — captured as the eval signal. Nothing is published."""
        self._pending_or_raise(draft_id)
        self.backend.resolve_draft(draft_id, status="rejected", review_note=reason)
        return ReviewResult(draft_id=draft_id, status="rejected", published=False,
                            review_note=reason)

    def _pending_or_raise(self, draft_id: str) -> dict:
        rec = self.backend.get_draft(draft_id)
        if rec is None:
            raise KeyError(f"no draft {draft_id!r}")
        if rec["status"] != "pending_review":
            raise ValueError(f"draft {draft_id!r} is {rec['status']}, not pending_review")
        return rec
