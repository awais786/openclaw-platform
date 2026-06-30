from openclaw.library import Doc, load_library, save_library, upload_pdfs


class FakeLLM:
    def upload_pdf(self, path: str) -> str:
        import os
        return "file_" + os.path.basename(path)


def test_upload_pdfs_returns_docs():
    docs = upload_pdfs(["/x/refunds.pdf", "/y/hours.pdf"], FakeLLM())
    assert [d.name for d in docs] == ["refunds.pdf", "hours.pdf"]
    assert docs[0].file_id == "file_refunds.pdf"


def test_save_load_round_trip(tmp_path):
    path = tmp_path / "lib.json"
    docs = [Doc("file_1", "a.pdf"), Doc("file_2", "b.pdf")]
    save_library(docs, path)
    assert load_library(path) == docs


def test_load_missing_returns_empty(tmp_path):
    assert load_library(tmp_path / "nope.json") == []
