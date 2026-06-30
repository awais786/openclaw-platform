"""OpenClaw — draft contact-us replies grounded in a knowledge base, using Claude.

The knowledge source is pluggable (KnowledgeBackend). The default backend has Claude read PDFs
uploaded to the Anthropic Files API; swap in a RAG/other backend by implementing the protocol.
"""

from .backends import FilesApiBackend, KnowledgeBackend
from .library import Doc, load_library, save_library, upload_pdfs
from .llm import ClaudeLLM
from .reply import Reply, draft_reply

__version__ = "0.4.0"
__all__ = [
    "ClaudeLLM",
    "Doc",
    "Reply",
    "draft_reply",
    "KnowledgeBackend",
    "FilesApiBackend",
    "upload_pdfs",
    "save_library",
    "load_library",
    "__version__",
]
