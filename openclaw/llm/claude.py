"""ClaudeLLM — Anthropic-backed implementation of LLMClient.

Uses the official `anthropic` SDK. Defaults: claude-opus-4-8 for drafting,
claude-haiku-4-5 for classification (set per-call via the `model` arg). The
zero-arg client resolves credentials from the environment (ANTHROPIC_API_KEY or
an `ant auth login` profile) — we don't hardcode a key.
"""
from __future__ import annotations

from .client import LLMResult

DEFAULT_MODEL = "claude-opus-4-8"


class ClaudeLLM:
    def __init__(self, default_model: str = DEFAULT_MODEL) -> None:
        import anthropic  # imported lazily so the package installs without it

        self._client = anthropic.Anthropic()
        self._default_model = default_model

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
        response_schema: dict | None = None,
    ) -> LLMResult:
        kwargs: dict = {
            "model": model or self._default_model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        # Structured output (e.g. intent classification) — guarantees parseable JSON.
        if response_schema is not None:
            kwargs["output_config"] = {
                "format": {"type": "json_schema", "schema": response_schema}
            }

        resp = self._client.messages.create(**kwargs)

        if resp.stop_reason == "refusal":
            # Safety classifier declined — surface, don't crash on empty content.
            return LLMResult(text="", model=resp.model, meta={"refusal": True})

        text = next((b.text for b in resp.content if b.type == "text"), "")
        return LLMResult(
            text=text,
            model=resp.model,
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
        )
