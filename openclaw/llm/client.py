"""Provider-agnostic LLM interface.

Phase 1 calls the model at exactly two steps: classify and draft. Keep concrete
providers behind this Protocol so the pipeline never hard-codes a vendor and so
classify vs. draft can use different (e.g. cheaper) models.

Implementations:
  - ClaudeLLM (openclaw.llm.claude)  — real Anthropic-backed client
  - EchoLLM                          — dependency-free stub so the engine runs offline
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LLMResult:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    meta: dict = field(default_factory=dict)


class LLMClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
        response_schema: dict | None = None,
    ) -> LLMResult:
        """Single-turn completion.

        Inbound/customer text must be passed as *data* inside `user`, never merged
        into `system` (prompt-injection defense). When `response_schema` is given,
        the returned `text` is JSON conforming to that schema.
        """
        ...


class EchoLLM:
    """Dependency-free stand-in so the engine runs with no provider key.
    Replace with ClaudeLLM in production (Engine does this automatically when a
    key is available)."""

    def __init__(self, model: str = "echo-1") -> None:
        self._model = model

    def complete(
        self, *, system, user, model=None, max_tokens=1024, response_schema=None
    ) -> LLMResult:
        if response_schema is not None:
            # Minimal valid object for the classify step so the local demo works.
            return LLMResult(text=json.dumps({"intent": "general", "confidence": 0.8}),
                             model=model or self._model)
        return LLMResult(text=f"[draft based on]: {user[:280]}", model=model or self._model)
