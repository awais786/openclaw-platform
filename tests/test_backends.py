from openclaw.backends import FilesApiBackend
from openclaw.library import Doc


class FakeLLM:
    def reply_from_pdfs(self, *, system, message, docs, max_tokens=1024):
        self.docs = docs
        return "Refunds within 14 days. [refunds.pdf]", ["refunds.pdf"]


def test_files_api_backend_grounded():
    llm = FakeLLM()
    backend = FilesApiBackend(llm, [Doc("f1", "refunds.pdf")])
    reply = backend.draft_reply("How do refunds work?")
    assert reply.grounded is True
    assert reply.citations == ["refunds.pdf"]
    assert llm.docs[0].name == "refunds.pdf"


def test_files_api_backend_no_docs_is_ungrounded():
    reply = FilesApiBackend(FakeLLM(), []).draft_reply("anything")
    assert reply.grounded is False
    assert reply.text == ""
