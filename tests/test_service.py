from openclaw.library import Doc, save_library
from openclaw.service import contact_us_reply, knowledge_base


class FakeLLM:
    def reply_from_pdfs(self, *, system, message, docs, max_tokens=1024):
        return "Refunds are available within 14 days. [refunds.pdf]", ["refunds.pdf"]


def test_contact_us_reply_grounded(tmp_path):
    lib = tmp_path / "lib.json"
    save_library([Doc("f1", "refunds.pdf")], lib)
    out = contact_us_reply("How do refunds work?", llm=FakeLLM(), library_path=str(lib))
    assert out["grounded"] is True
    assert out["citations"] == ["refunds.pdf"]
    assert out["text"]


def test_contact_us_reply_no_kb(tmp_path):
    out = contact_us_reply("anything", llm=FakeLLM(), library_path=str(tmp_path / "missing.json"))
    assert out["grounded"] is False
    assert out["text"] == ""


def test_knowledge_base_lists_names(tmp_path):
    lib = tmp_path / "lib.json"
    save_library([Doc("f1", "a.pdf"), Doc("f2", "b.pdf")], lib)
    assert knowledge_base(str(lib)) == ["a.pdf", "b.pdf"]
