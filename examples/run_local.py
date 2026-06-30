"""Run OpenClaw directly — no Django, no provider key.

    python -m examples.run_local

Wires the in-memory LocalBackend + a stub LLM and pushes one contact-us message
through the propose-then-approve pipeline.
"""
from openclaw.connectors.contactus import ContactUsConnector
from openclaw.llm.client import EchoLLM
from openclaw.runtime.pipeline import Pipeline
from openclaw.tools.backends.local import LocalBackend
from openclaw.tools.schemas import KBChunk


def main() -> None:
    kb = [
        KBChunk(chunk_id="kb1", doc_id="faq", score=0.9,
                text="To reset your password, open Settings > Security and click Reset."),
        KBChunk(chunk_id="kb2", doc_id="faq", score=0.8,
                text="Refunds are handled case by case by the billing team."),
    ]
    backend = LocalBackend(kb=kb)
    pipe = Pipeline(backend, EchoLLM())

    raw = {"id": 1001, "email": "user@example.com",
           "message": "How do I reset my password?"}
    msg = ContactUsConnector().normalize(raw)
    draft = pipe.handle(msg)

    print("intent     :", draft.intent)
    print("status     :", draft.status, "(human approves before send in Phase 1)")
    print("citations  :", draft.citations)
    print("draft text :", draft.text)


if __name__ == "__main__":
    main()
