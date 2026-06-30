"""ClaudeLLM — minimal Anthropic-backed text completion.

Zero-arg client resolves credentials from the environment (ANTHROPIC_API_KEY or
an `ant auth login` profile). Default model: claude-opus-4-8.
"""
from __future__ import annotations

DEFAULT_MODEL = "claude-opus-4-8"


class ClaudeLLM:
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        import anthropic

        self._client = anthropic.Anthropic()
        self.model = model

    def complete(self, *, system: str, user: str, max_tokens: int = 1024) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if resp.stop_reason == "refusal":
            return ""
        return next((b.text for b in resp.content if b.type == "text"), "")
