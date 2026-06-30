"""ClaudeLLM — Anthropic-backed: upload PDFs and answer from them directly.

No vector DB or retrieval. PDFs are uploaded once to the Files API; each reply hands
Claude the PDFs (by file_id) plus the customer message, with citations enabled.
Zero-arg client resolves credentials from the env (ANTHROPIC_API_KEY / `ant auth login`).
"""
from __future__ import annotations

import os

DEFAULT_MODEL = "claude-opus-4-8"
_FILES_BETA = "files-api-2025-04-14"


class ClaudeLLM:
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        import anthropic

        self._client = anthropic.Anthropic()
        self.model = model

    def upload_pdf(self, path: str) -> str:
        """Upload one PDF to the Files API; return its reusable file_id."""
        with open(path, "rb") as f:
            uploaded = self._client.beta.files.upload(
                file=(os.path.basename(path), f, "application/pdf")
            )
        return uploaded.id

    def reply_from_pdfs(self, *, system: str, message: str, docs, max_tokens: int = 1024):
        """Answer `message` from the given PDFs. Returns (text, citations) where
        citations are the document titles Claude actually cited."""
        content = [
            {
                "type": "document",
                "source": {"type": "file", "file_id": d.file_id},
                "title": d.name,
                "citations": {"enabled": True},
            }
            for d in docs
        ]
        content.append(
            {"type": "text", "text": f"<customer_message>\n{message}\n</customer_message>"}
        )

        resp = self._client.beta.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            betas=[_FILES_BETA],
            system=system,
            messages=[{"role": "user", "content": content}],
        )
        if resp.stop_reason == "refusal":
            return "", []

        parts: list[str] = []
        cited: list[str] = []
        for block in resp.content:
            if block.type != "text":
                continue
            parts.append(block.text)
            for c in getattr(block, "citations", None) or []:
                title = getattr(c, "document_title", None) or "source"
                if title not in cited:
                    cited.append(title)
        return "".join(parts), cited
