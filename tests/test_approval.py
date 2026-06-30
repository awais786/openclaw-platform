"""End-to-end Contact-Us scenario: submit -> queue -> human approve/edit/reject -> publish.

Uses the offline EchoLLM stub + LocalBackend, so no provider key is needed.
"""
import pytest

from openclaw.config import Settings
from openclaw.engine import Engine
from openclaw.tools.schemas import KBChunk

_KB = [KBChunk(chunk_id="kb1", doc_id="faq", score=0.9,
               text="reset your password in Settings > Security")]


def _engine():
    return Engine.from_settings(Settings(), kb=_KB)


def _submit(engine, external_id="1"):
    return engine.handle_raw("contactus", {
        "id": external_id, "email": "user@example.com",
        "message": "How do I reset my password?",
    })


def _outbound(engine, thread_key):
    return [m for m in engine.backend.get_conversation(thread_key) if m["direction"] == "outbound"]


def test_submit_queues_a_pending_draft():
    engine = _engine()
    draft = _submit(engine)
    assert draft.status == "pending_review"
    assert draft.draft_id
    pending = engine.pending()
    assert [d["id"] for d in pending] == [draft.draft_id]


def test_approve_publishes_and_clears_the_queue():
    engine = _engine()
    draft = _submit(engine)

    result = engine.approve(draft.draft_id, reviewer="alice")

    assert result.status == "approved"
    assert result.published is True
    assert _outbound(engine, "contactus:1")            # reply was published
    assert engine.pending() == []                       # left the queue


def test_edit_approve_publishes_edited_text_and_records_diff():
    engine = _engine()
    draft = _submit(engine)

    result = engine.approve(draft.draft_id, reviewer="alice", edited_text="Edited reply.")

    assert result.status == "edited"
    assert result.published is True
    assert result.edit_diff                              # eval signal captured
    out = _outbound(engine, "contactus:1")
    assert out[-1]["text"] == "Edited reply."


def test_reject_records_reason_and_does_not_publish():
    engine = _engine()
    draft = _submit(engine)

    result = engine.reject(draft.draft_id, reviewer="alice", reason="off-policy tone")

    assert result.status == "rejected"
    assert result.published is False
    assert result.review_note == "off-policy tone"
    assert _outbound(engine, "contactus:1") == []       # nothing published
    assert engine.pending() == []


def test_cannot_review_the_same_draft_twice():
    engine = _engine()
    draft = _submit(engine)
    engine.approve(draft.draft_id, reviewer="alice")
    with pytest.raises(ValueError):
        engine.approve(draft.draft_id, reviewer="bob")
