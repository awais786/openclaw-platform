from openclaw.kb import KnowledgeBase
from openclaw.reply import draft_reply


class FakeLLM:
    """Records the prompt and returns a canned answer — no network/key needed."""

    def __init__(self) -> None:
        self.last_user = None

    def complete(self, *, system, user, max_tokens=1024):
        self.last_user = user
        return "Open Settings > Security and click Reset. [password.md]"


def _kb():
    kb = KnowledgeBase()
    kb.add("password.md", "To reset your password, open Settings > Security and click Reset.")
    return kb


def test_grounded_reply_cites_sources_and_passes_context_to_llm():
    llm = FakeLLM()
    reply = draft_reply("How do I reset my password?", _kb(), llm)
    assert reply.grounded is True
    assert reply.citations == ["password.md"]
    assert reply.text
    assert "Settings > Security" in llm.last_user   # KB context reached the model


def test_no_kb_match_does_not_call_the_llm():
    llm = FakeLLM()
    reply = draft_reply("totally unrelated question", KnowledgeBase(), llm)
    assert reply.grounded is False
    assert reply.text == ""
    assert llm.last_user is None                     # model never called without grounding
