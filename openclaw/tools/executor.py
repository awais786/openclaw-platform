"""ToolExecutor — the single choke point for every write/action tool.

Read tools may be called on the backend directly. Every SIDE EFFECT must go through
here so capability gating, idempotency, and ToolCall audit logging are enforced in one
place — for every backend, in every phase. If a write tool can be called without the
executor, the gate has a hole.
"""
from __future__ import annotations

from .backend import ToolBackend
from .schemas import Draft, GateDecision, NormalizedMessage

# Actions that can NEVER be auto-executed, regardless of policy or metrics.
HARD_WALL = {"issue_refund"}


class ToolExecutor:
    def __init__(self, backend: ToolBackend) -> None:
        self.backend = backend

    def _gate(self, action: str, *, channel: str, intent: str) -> GateDecision:
        if action in HARD_WALL:
            return GateDecision.BLOCKED          # always requires a human, elsewhere
        mode = self.backend.gate_mode(action, channel=channel, intent=intent)
        if mode == "auto":
            return GateDecision.AUTO
        if mode == "never_auto":
            return GateDecision.BLOCKED
        return GateDecision.QUEUED               # human_approval

    def _audit(self, action: str, decision: GateDecision, key: str, error: str | None = None):
        self.backend.log_tool_call({
            "tool_name": action,
            "gate_decision": decision.value,
            "idempotency_key": key,
            "error": error,
        })

    # ----- write/action entry points -----
    def save_conversation(self, msg: NormalizedMessage, *, idempotency_key: str) -> str:
        # storage is not gated, but is still audited + idempotent
        out = self.backend.save_conversation(msg, idempotency_key=idempotency_key)
        self._audit("save_conversation", GateDecision.AUTO, idempotency_key)
        return out

    def save_draft(self, thread_key: str, draft: Draft, *, idempotency_key: str) -> str:
        out = self.backend.save_draft(thread_key, draft, idempotency_key=idempotency_key)
        self._audit("save_draft", GateDecision.AUTO, idempotency_key)
        return out

    def publish_reply(
        self, thread_key: str, text: str, *, channel: str, intent: str,
        idempotency_key: str, approved_by: str | None = None,
    ) -> tuple[GateDecision, str | None]:
        decision = self._gate("publish_reply", channel=channel, intent=intent)
        if decision is GateDecision.QUEUED and not approved_by:
            self._audit("publish_reply", decision, idempotency_key)
            return decision, None                # waits for human approval
        if decision is GateDecision.BLOCKED:
            self._audit("publish_reply", decision, idempotency_key, error="blocked by policy")
            return decision, None
        out = self.backend.publish_reply(thread_key, text, idempotency_key=idempotency_key)
        self._audit("publish_reply",
                    GateDecision.APPROVED if approved_by else GateDecision.AUTO, idempotency_key)
        return decision, out

    def route_to_human(self, thread_key: str, intent: str, reason: str) -> None:
        self.backend.route_to_human(thread_key, intent, reason)
        self._audit("route_to_human", GateDecision.AUTO, thread_key)
