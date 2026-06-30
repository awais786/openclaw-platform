"""Capability gating: write actions are gated; the refund hard wall always blocks."""
from openclaw.tools.backends.local import LocalBackend
from openclaw.tools.executor import HARD_WALL, ToolExecutor
from openclaw.tools.schemas import GateDecision


def test_publish_reply_is_queued_by_default():
    ex = ToolExecutor(LocalBackend())
    decision, out = ex.publish_reply("t1", "hi", channel="contactus", intent="general",
                                     idempotency_key="k1")
    assert decision is GateDecision.QUEUED   # human_approval default -> not published
    assert out is None


def test_publish_reply_after_human_approval():
    ex = ToolExecutor(LocalBackend())
    decision, out = ex.publish_reply("t1", "hi", channel="contactus", intent="general",
                                     idempotency_key="k1", approved_by="reviewer")
    assert out is not None   # approved -> published


def test_refund_is_hard_walled():
    assert "issue_refund" in HARD_WALL
