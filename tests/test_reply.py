from openclaw.library import Doc
from openclaw.reply import draft_reply


class FakeLLM:
    """Returns a cited answer; records what it was given. No key/anthropic needed."""

    def __init__(self) -> None:
        self.called = False
        self.docs = None

    def reply_from_pdfs(self, *, system, message, docs, max_tokens=1024):
        self.called = True
        self.docs = docs
        return "You can get a refund within 14 days. [refunds.pdf]", ["refunds.pdf"]


class PuntLLM:
    """Simulates Claude declining to answer — no citations."""

    def reply_from_pdfs(self, *, system, message, docs, max_tokens=1024):
        return "I don't have that information.", []


def test_grounded_reply_cites_sources_and_passes_docs():
    llm = FakeLLM()
    reply = draft_reply("How do refunds work?", [Doc("f1", "refunds.pdf")], llm)
    assert reply.grounded is True
    assert reply.citations == ["refunds.pdf"]
    assert reply.text
    assert llm.docs[0].name == "refunds.pdf"   # the PDF reached the model


def test_no_pdfs_does_not_call_the_llm():
    llm = FakeLLM()
    reply = draft_reply("anything", [], llm)
    assert reply.grounded is False
    assert reply.text == ""
    assert llm.called is False


def test_uncited_answer_is_not_grounded():
    reply = draft_reply("obscure question", [Doc("f1", "refunds.pdf")], PuntLLM())
    assert reply.grounded is False   # no citations -> escalate
