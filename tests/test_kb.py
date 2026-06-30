from openclaw.kb import KnowledgeBase


def test_search_ranks_relevant_chunks():
    kb = KnowledgeBase()
    kb.add("password.md", "To reset your password, open Settings.")
    kb.add("hours.md", "Support hours are 9am to 6pm.")
    hits = kb.search("how do I reset my password")
    assert hits[0].id == "password.md"
    assert hits[0].score > 0


def test_search_returns_empty_when_nothing_matches():
    kb = KnowledgeBase()
    kb.add("hours.md", "Support hours are 9am to 6pm.")
    assert kb.search("quantum entanglement refund policy") == []


def test_from_dir_loads_md_and_txt(tmp_path):
    (tmp_path / "a.md").write_text("alpha content")
    (tmp_path / "b.txt").write_text("beta content")
    (tmp_path / "ignore.json").write_text("{}")
    kb = KnowledgeBase.from_dir(tmp_path)
    ids = {c.id for c in kb.search("alpha beta content")}
    assert ids == {"a.md", "b.txt"}
