"""Contact-Us connector — Phase 1's first channel (private, owned, no third-party ToS)."""
from __future__ import annotations

from ..tools.schemas import NormalizedMessage


class ContactUsConnector:
    channel = "contactus"

    def normalize(self, raw: dict) -> NormalizedMessage:
        submission_id = str(raw["id"])
        return NormalizedMessage(
            channel=self.channel,
            external_id=submission_id,                 # idempotency / dedup key
            thread_key=f"contactus:{submission_id}",
            text=raw.get("message", ""),
            customer_ref=raw.get("email", "unknown"),
        )
