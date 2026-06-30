"""Knowledge base: store text chunks and retrieve the most relevant for a query.

Keyword overlap scoring for now — good enough to ground replies and dependency-free.
Swap search() for embeddings later without changing callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    id: str
    text: str
    score: float = 0.0


class KnowledgeBase:
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def add(self, chunk_id: str, text: str) -> None:
        self._chunks.append(Chunk(id=chunk_id, text=text))

    @classmethod
    def from_dir(cls, path: str | Path) -> KnowledgeBase:
        """Load every .md / .txt file under `path` as a chunk (filename = id)."""
        kb = cls()
        for f in sorted(Path(path).glob("**/*")):
            if f.is_file() and f.suffix in {".md", ".txt"}:
                kb.add(f.name, f.read_text())
        return kb

    def search(self, query: str, k: int = 4) -> list[Chunk]:
        words = {w for w in query.lower().split() if len(w) > 2}
        hits = []
        for c in self._chunks:
            text = c.text.lower()
            overlap = sum(1 for w in words if w in text)
            if overlap:
                hits.append(Chunk(id=c.id, text=c.text, score=overlap / max(len(words), 1)))
        return sorted(hits, key=lambda c: c.score, reverse=True)[:k]
