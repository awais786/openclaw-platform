"""Engine — the one obvious entry point for wiring OpenClaw.

    from openclaw import Engine
    engine = Engine.from_settings()          # auto-selects provider + backend
    draft = engine.handle_raw("contactus", {"id": 1, "email": "...", "message": "..."})

Auto-selection:
  - LLM:     ClaudeLLM if the `anthropic` SDK + credentials are available, else EchoLLM.
  - Backend: LocalBackend (default) or DjangoBackend when settings.backend == "django".
"""
from __future__ import annotations

import logging
import os

from .config import Settings
from .connectors.base import Connector
from .connectors.contactus import ContactUsConnector
from .llm.client import EchoLLM, LLMClient
from .runtime.pipeline import Pipeline
from .tools.backend import ToolBackend
from .tools.backends.local import LocalBackend
from .tools.schemas import Draft, KBChunk

log = logging.getLogger("openclaw")

_CONNECTORS: dict[str, Connector] = {
    "contactus": ContactUsConnector(),
}


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
