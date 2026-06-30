"""DjangoBackend — talks to the Django app over REST.

Same ToolBackend contract as LocalBackend; only the transport differs. This is what
makes "use OpenClaw directly, connect Django when needed" true: point the engine at a
running backend_django service and you gain persistence, approval workflow, RBAC, audit.

NOTE: endpoint paths are placeholders — align with backend_django's REST API (ticket #3).
"""
from __future__ import annotations

import httpx

from ..schemas import Customer, Draft, KBChunk, NormalizedMessage


class DjangoBackend:
    def __init__(self, base_url: str, token: str, timeout: float = 10.0) -> None:
        self._c = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )

    def _get(self, path: str, **params):
        r = self._c.get(path, params=params)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json: dict):
        r = self._c.post(path, json=json)
        r.raise_for_status()
        return r.json()

    # ----- read -----
    def get_customer(self, external_id: str) -> Customer | None:
        data = self._get("/api/customers/lookup", external_id=external_id)
        return Customer(**data) if data else None

    def get_conversation(self, thread_key: str) -> list[dict]:
        return self._get("/api/conversations", thread_key=thread_key).get("messages", [])

    def search_kb(self, query: str, intent: str | None = None, k: int = 5) -> list[KBChunk]:
        data = self._get("/api/kb/search", q=query, intent=intent or "", k=k)
        return [KBChunk(**c) for c in data.get("results", [])]

    def lookup_subscription(self, customer_id: str) -> dict | None:
        return self._get("/api/subscriptions", customer_id=customer_id)

    def refund_eligibility(self, customer_id: str, order_id: str) -> dict:
        return self._get("/api/refund-eligibility", customer_id=customer_id, order_id=order_id)

    # ----- write -----
    def save_conversation(self, msg: NormalizedMessage, *, idempotency_key: str) -> str:
        return self._post("/api/conversations/save",
                          {"msg": msg.__dict__, "idempotency_key": idempotency_key})["id"]

    def save_draft(self, thread_key: str, draft: Draft, *, idempotency_key: str) -> str:
        return self._post("/api/drafts/save",
                          {"thread_key": thread_key, "draft": draft.__dict__,
                           "idempotency_key": idempotency_key})["id"]

    def publish_reply(self, thread_key: str, text: str, *, idempotency_key: str) -> str:
        return self._post("/api/replies/publish",
                          {"thread_key": thread_key, "text": text,
                           "idempotency_key": idempotency_key})["id"]

    def route_to_human(self, thread_key: str, intent: str, reason: str) -> None:
        self._post("/api/route-to-human",
                   {"thread_key": thread_key, "intent": intent, "reason": reason})

    def gate_mode(self, action: str, *, channel: str, intent: str) -> str:
        return self._get("/api/capability-policy",
                         action=action, channel=channel, intent=intent)["mode"]

    def log_tool_call(self, record: dict) -> None:
        self._post("/api/tool-calls", record)
