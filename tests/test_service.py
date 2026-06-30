from openclaw.library import Doc, save_library
from openclaw.reply import Reply
from openclaw.service import contact_us_reply, knowledge_base


class StubBackend:
    """Any object with draft_reply(message) -> Reply works — proves the seam is agnostic."""

    def __init__(self, reply: Reply) -> None:
        self._reply = reply

    def draft_reply(self, message: str) -> Reply:
        return self._reply


def test_contact_us_reply_passes_backend_result_through():
    backend = StubBackend(Reply(text="Answer.", citations=["refunds.pdf"], grounded=True))
    out = contact_us_reply("How do refunds work?", backend=backend)
    assert out == {"text": "Answer.", "citations": ["refunds.pdf"], "grounded": True}


def test_contact_us_reply_ungrounded():
    out = contact_us_reply("obscure", backend=StubBackend(Reply(text="", grounded=False)))
    assert out["grounded"] is False


def test_knowledge_base_lists_names(tmp_path):
    lib = tmp_path / "lib.json"
    save_library([Doc("f1", "a.pdf"), Doc("f2", "b.pdf")], lib)
    assert knowledge_base(str(lib)) == ["a.pdf", "b.pdf"]
