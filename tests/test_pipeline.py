"""Pipeline behavior with the offline EchoLLM stub (no provider key needed)."""
from openclaw.config import Settings
from openclaw.llm.client import EchoLLM
from openclaw.runtime.pipeline import Pipeline
from openclaw.tools.backends.local import LocalBackend
from openclaw.tools.schemas import KBChunk, NormalizedMessage


def _msg(external_id="1", text="How do I reset my password?"):
    return NormalizedMessage(channel="contactus", external_id=external_id,
                             thread_key=f"contactus:{external_id}", text=text,
                             customer_ref="user@example.com")


_DEFAULT_KB = [KBChunk(chunk_id="kb1", doc_id="faq", score=0.9,
                       text="reset your password in Settings")]


def _pipe(kb=None):
    backend = LocalBackend(kb=_DEFAULT_KB if kb is None else kb)
    return Pipeline(backend, EchoLLM(), Settings())


def test_grounded_message_yields_pending_review():
    draft = _pipe().handle(_msg())
    assert draft.status == "pending_review"   # never auto-sent in Phase 1
    assert draft.citations == ["kb1"]
    assert draft.text


def test_no_kb_grounding_routes_to_human():
    # Empty KB -> nothing above threshold -> needs_human, no parametric answer.
    draft = _pipe(kb=[]).handle(_msg())
    assert draft.status == "needs_human"
    assert draft.text == ""


def test_dedup_is_idempotent():
    backend = LocalBackend(kb=[KBChunk(chunk_id="kb1", doc_id="faq", score=0.9,
                                       text="reset password")])
    pipe = Pipeline(backend, EchoLLM(), Settings())
    pipe.handle(_msg(external_id="dup"))
    pipe.handle(_msg(external_id="dup"))
    inbound = [m for m in backend.get_conversation("contactus:dup") if m["direction"] == "inbound"]
    assert len(inbound) == 1   # second identical message deduped
