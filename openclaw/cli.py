"""`openclaw` CLI — run a message through the pipeline from the terminal.

    openclaw demo
    openclaw run --message "How do I reset my password?" --email user@example.com

Uses Settings.from_env() — set ANTHROPIC_API_KEY to use Claude; otherwise the
offline EchoLLM stub runs. The demo seeds a tiny in-memory KB.
"""
from __future__ import annotations

import argparse
import logging

from .config import Settings
from .engine import Engine
from .tools.schemas import KBChunk

_DEMO_KB = [
    KBChunk(chunk_id="kb1", doc_id="faq", score=0.9,
            text="To reset your password, open Settings > Security and click Reset."),
    KBChunk(chunk_id="kb2", doc_id="faq", score=0.8,
            text="Our support hours are 9am-6pm PT, Monday through Friday."),
]


def _print_draft(draft) -> None:
    print(f"intent     : {draft.intent}")
    print(f"confidence : {draft.confidence}")
    print(f"status     : {draft.status}  (human approves before send in Phase 1)")
    print(f"citations  : {draft.citations}")
    print(f"model      : {draft.model}")
    print(f"draft text : {draft.text}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openclaw", description="OpenClaw engine CLI")
    parser.add_argument("-v", "--verbose", action="store_true", help="enable info logging")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="run a sample contact-us message through the pipeline")

    run = sub.add_parser("run", help="run a single message")
    run.add_argument("--message", required=True)
    run.add_argument("--email", default="user@example.com")
    run.add_argument("--channel", default="contactus")
    run.add_argument("--id", default="1")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING)

    settings = Settings.from_env()

    if args.cmd == "demo":
        engine = Engine.from_settings(settings, kb=_DEMO_KB)
        draft = engine.handle_raw("contactus",
                                  {"id": 1001, "email": "user@example.com",
                                   "message": "How do I reset my password?"})
        _print_draft(draft)
        return 0

    if args.cmd == "run":
        engine = Engine.from_settings(settings, kb=_DEMO_KB)
        draft = engine.handle_raw(
            args.channel,
            {"id": args.id, "email": args.email, "message": args.message},
        )
        _print_draft(draft)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
