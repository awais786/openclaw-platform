"""Provider-agnostic LLM interface.

Phase 1 calls the model at exactly two steps: classify and draft. Keep concrete
providers behind this Protocol so the pipeline never hard-codes a vendor and so
classify vs. draft can use different (e.g. cheaper) models.
"""
from __future__ import annotations

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
    def complete(self, *, system: str, user: str, model: str | None = None) -> LLMResult:
        """Single-turn completion. Inbound/customer text must be passed as *data*
        inside `user`, never merged into `system` (prompt-injection defense)."""
        ...


class EchoLLM:
    """Trivial stand-in so the engine runs standalone without a provider key.
    Replace with a real provider client in production."""

    def __init__(self, model: str = "echo-1") -> None:
        self._model = model

    def complete(self, *, system: str, user: str, model: str | None = None) -> LLMResult:
        return LLMResult(text=f"[draft based on]: {user[:280]}", model=model or self._model)
