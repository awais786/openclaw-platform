"""Tool schemas and shared value types — the OpenClaw <-> backend contract.

The agent is given ONLY these schemas; it never sees an ORM, SQL, or HTTP detail.
Both LocalBackend and DjangoBackend implement the same contract.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class GateMode(str, enum.Enum):
    AUTO = "auto"
    HUMAN_APPROVAL = "human_approval"
    NEVER_AUTO = "never_auto"   # hard wall — metrics can never promote


class GateDecision(str, enum.Enum):
    AUTO = "auto"
    APPROVED = "approved"
    QUEUED = "queued"          # waiting on a human
    BLOCKED = "blocked"        # refused (e.g. never_auto without human)


# ---- read-tool returns ----
@dataclass
class KBChunk:
    chunk_id: str
    doc_id: str
    text: str
    score: float
    source_uri: str | None = None


@dataclass
class Customer:
    customer_id: str
    external_ids: dict = field(default_factory=dict)
    name: str | None = None
    vip: bool = False


# ---- pipeline values ----
@dataclass
class NormalizedMessage:
    channel: str
    external_id: str          # unique per channel — idempotency key
    thread_key: str
    text: str
    customer_ref: str         # email / username / submission id


@dataclass
class Draft:
    text: str
    intent: str
    confidence: float
    citations: list[str]              # KBChunk ids
    status: str                       # pending_review | auto_approved | needs_human
    prompt_version: str = "v1"
    model: str | None = None


@dataclass
class ToolResult:
    ok: bool
    value: object = None
    gate_decision: GateDecision | None = None
    error: str | None = None
