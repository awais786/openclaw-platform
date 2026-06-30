"""Settings — env-driven config with sane defaults.

Load once via Settings.from_env(); pass the result into the Engine. Keeps model
choice, thresholds, and backend selection out of the code and in the environment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # LLM
    draft_model: str = "claude-opus-4-8"        # most capable — used for the reply draft
    classify_model: str = "claude-haiku-4-5"    # cheap + fast — used for intent classification
    draft_max_tokens: int = 1024
    classify_max_tokens: int = 256

    # Pipeline thresholds
    sim_threshold: float = 0.30                 # min KB similarity to ground a draft
    conf_threshold: float = 0.55                # min intent confidence to auto-draft

    # Backend: "local" (in-memory) or "django" (REST)
    backend: str = "local"
    django_base_url: str = "http://localhost:8000"
    django_token: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        def _f(name: str, default: float) -> float:
            v = os.environ.get(name)
            return float(v) if v else default

        def _i(name: str, default: int) -> int:
            v = os.environ.get(name)
            return int(v) if v else default

        return cls(
            draft_model=os.environ.get("OPENCLAW_DRAFT_MODEL", cls.draft_model),
            classify_model=os.environ.get("OPENCLAW_CLASSIFY_MODEL", cls.classify_model),
            draft_max_tokens=_i("OPENCLAW_DRAFT_MAX_TOKENS", cls.draft_max_tokens),
            classify_max_tokens=_i("OPENCLAW_CLASSIFY_MAX_TOKENS", cls.classify_max_tokens),
            sim_threshold=_f("OPENCLAW_SIM_THRESHOLD", cls.sim_threshold),
            conf_threshold=_f("OPENCLAW_CONF_THRESHOLD", cls.conf_threshold),
            backend=os.environ.get("OPENCLAW_BACKEND", cls.backend),
            django_base_url=os.environ.get("OPENCLAW_DJANGO_URL", cls.django_base_url),
            django_token=os.environ.get("OPENCLAW_DJANGO_TOKEN", cls.django_token),
        )
