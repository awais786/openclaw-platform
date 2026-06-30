"""openclaw — contact-us replies grounded in PDFs, via Claude.

    openclaw upload faq.pdf refunds.pdf      # upload once → saves the library
    openclaw reply --message "How do refunds work?"
"""
from __future__ import annotations

import argparse
import sys

from .library import load_library, save_library, upload_pdfs
from .llm import ClaudeLLM
from .reply import draft_reply

DEFAULT_LIBRARY = "openclaw_library.json"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="openclaw", description="Contact-us replies grounded in PDFs, via Claude"
    )
    p.add_argument("--library", default=DEFAULT_LIBRARY, help="path to the file-id library JSON")
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("upload", help="upload PDFs to the Files API and save the library")
    up.add_argument("pdfs", nargs="+", help="paths to PDF files")

    rp = sub.add_parser("reply", help="draft a reply to a contact-us message")
    rp.add_argument("--message", required=True)

    args = p.parse_args(argv)

    try:
        llm = ClaudeLLM()
    except Exception as e:  # noqa: BLE001 — surface client-init failure plainly
        print(f"Could not initialize Claude client: {e}\n"
              "Set ANTHROPIC_API_KEY or run `ant auth login`.", file=sys.stderr)
        return 2

    if args.cmd == "upload":
        docs = upload_pdfs(args.pdfs, llm)
        save_library(docs, args.library)
        print(f"Uploaded {len(docs)} PDF(s) → {args.library}")
        for d in docs:
            print(f"  {d.name}  {d.file_id}")
        return 0

    if args.cmd == "reply":
        docs = load_library(args.library)
        if not docs:
            print(f"No PDFs in {args.library}. Run: openclaw upload <file.pdf>", file=sys.stderr)
            return 1
        reply = draft_reply(args.message, docs, llm)
        if not reply.grounded:
            print("No grounded answer in the PDFs — escalate to a human.")
            return 0
        print(reply.text)
        print(f"\n[sources: {', '.join(reply.citations)}]")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
