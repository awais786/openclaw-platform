"""The knowledge base = a small set of PDFs uploaded to the Files API.

Each Doc is an uploaded PDF (file_id + filename). Upload once, persist the ids to a
small JSON file, and reuse them on every reply. No vector DB, no chunking.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Doc:
    file_id: str
    name: str


def upload_pdfs(paths: list[str], llm) -> list[Doc]:
    """Upload each PDF via the LLM client; return the resulting Docs."""
    return [Doc(file_id=llm.upload_pdf(p), name=Path(p).name) for p in paths]


def save_library(docs: list[Doc], path: str) -> None:
    Path(path).write_text(json.dumps([asdict(d) for d in docs], indent=2))


def load_library(path: str) -> list[Doc]:
    p = Path(path)
    if not p.exists():
        return []
    return [Doc(**d) for d in json.loads(p.read_text())]
