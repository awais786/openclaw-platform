"""LocalBackend — in-memory implementation so OpenClaw runs with no Django.

Good for dev, demos, tests, and lightweight standalone use. Swap for DjangoBackend
(same contract) to get real persistence, approval workflow, RBAC, and audit.
"""
from __future__ import annotations

from ..schemas import Customer, Draft, KBChunk, NormalizedMessage


class LocalBackend:
    def __init__(self, kb: list[KBChunk] | None = None) -> None:
        self._kb = kb or []
        self._seen: set[str] = set()           # idempotency keys
        self._conversations: dict[str, list[dict]] = {}
        self._tool_calls: list[dict] = []
        self._drafts: dict[str, dict] = {}     # draft_id -> review record
        # Default policy: everything needs a human; refunds/legal are hard-walled.
        self._policy = {
            "publish_reply": "human_approval",
            "issue_refund": "never_auto",
            "create_github_issue": "human_approval",
            "create_jira_ticket": "human_approval",
        }

    # ----- read -----
    def get_customer(self, external_id: str) -> Customer | None:
        return Customer(customer_id=external_id, external_ids={"ref": external_id})

    def get_conversation(self, thread_key: str) -> list[dict]:
        return self._conversations.get(thread_key, [])

    def search_kb(self, query: str, intent: str | None = None, k: int = 5) -> list[KBChunk]:
        q = query.lower()
        scored = [c for c in self._kb if any(w in c.text.lower() for w in q.split())]
        return sorted(scored, key=lambda c: c.score, reverse=True)[:k]

    def lookup_subscription(self, customer_id: str) -> dict | None:
        return {"customer_id": customer_id, "plan": "unknown"}

    def refund_eligibility(self, customer_id: str, order_id: str) -> dict:
        return {"eligible": False, "reason": "policy lookup not configured"}

    # ----- write -----
    def save_conversation(self, msg: NormalizedMessage, *, idempotency_key: str) -> str:
        if idempotency_key in self._seen:
            return "duplicate"
        self._seen.add(idempotency_key)
        self._conversations.setdefault(msg.thread_key, []).append(
            {"direction": "inbound", "text": msg.text}
        )
        return msg.thread_key

    def save_draft(self, thread_key: str, draft: Draft, *, idempotency_key: str) -> str:
        draft_id = f"d{len(self._drafts) + 1}"
        self._drafts[draft_id] = {
            "id": draft_id,
            "thread_key": thread_key,
            "channel": thread_key.split(":", 1)[0],   # connector sets "{channel}:{id}"
            "intent": draft.intent,
            "text": draft.text,
            "status": draft.status,
            "citations": draft.citations,
            "review_note": "",
            "edit_diff": "",
            "final_text": "",
        }
        self._conversations.setdefault(thread_key, []).append(
            {"direction": "draft", "draft_id": draft_id, "text": draft.text, "status": draft.status}
        )
        return draft_id

    def publish_reply(self, thread_key: str, text: str, *, idempotency_key: str) -> str:
        if idempotency_key in self._seen:
            return "duplicate"
        self._seen.add(idempotency_key)
        self._conversations.setdefault(thread_key, []).append(
            {"direction": "outbound", "text": text}
        )
        return f"published:{thread_key}"

    def route_to_human(self, thread_key: str, intent: str, reason: str) -> None:
        self._conversations.setdefault(thread_key, []).append(
            {"direction": "system", "text": f"routed to human ({intent}): {reason}"}
        )

    def gate_mode(self, action: str, *, channel: str, intent: str) -> str:
        return self._policy.get(action, "human_approval")

    def log_tool_call(self, record: dict) -> None:
        self._tool_calls.append(record)

    # ----- review queue -----
    def list_pending_drafts(self) -> list[dict]:
        return [d for d in self._drafts.values() if d["status"] == "pending_review"]

    def get_draft(self, draft_id: str) -> dict | None:
        return self._drafts.get(draft_id)

    def resolve_draft(
        self, draft_id: str, *, status: str, final_text: str = "",
        review_note: str = "", edit_diff: str = "",
    ) -> None:
        rec = self._drafts[draft_id]
        rec["status"] = status
        rec["final_text"] = final_text
        rec["review_note"] = review_note
        rec["edit_diff"] = edit_diff
