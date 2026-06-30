"""OpenClaw — draft contact-us replies grounded in PDFs, using Claude.

Upload PDFs once (Files API), then for each message Claude reads them and drafts a
grounded reply with citations. No vector DB, no retrieval index.
"""

from .library import Doc, load_library, save_library, upload_pdfs
from .llm import ClaudeLLM
from .reply import Reply, draft_reply

__version__ = "0.3.0"
__all__ = [
    "ClaudeLLM",
    "Doc",
    "Reply",
    "draft_reply",
    "upload_pdfs",
    "save_library",
    "load_library",
    "__version__",
]
