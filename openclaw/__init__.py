"""OpenClaw — draft contact-us replies grounded in a knowledge base, using Claude."""

from .kb import Chunk, KnowledgeBase
from .llm import ClaudeLLM
from .reply import Reply, draft_reply

__version__ = "0.2.0"
__all__ = ["KnowledgeBase", "Chunk", "ClaudeLLM", "Reply", "draft_reply", "__version__"]
