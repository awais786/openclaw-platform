"""openclaw — draft a contact-us reply from the knowledge base.

    openclaw --message "How do I reset my password?"
    openclaw --message "..." --docs ./kb     # load .md/.txt files as the KB
"""
from __future__ import annotations

import argparse
import sys

from .kb import KnowledgeBase
from .llm import ClaudeLLM
from .reply import draft_reply

_DEMO_DOCS = {
    "password.md": "To reset your password, open Settings > Security and click Reset.",
    "hours.md": "Support hours are 9am-6pm PT, Monday through Friday.",
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="openclaw", description="Draft a contact-us reply grounded in the knowledge base"
    )
    p.add_argument("--message", required=True, help="the incoming contact-us message")
    p.add_argument("--docs", help="directory of .md/.txt KB files (defaults to a tiny demo KB)")
    args = p.parse_args(argv)

    if args.docs:
        kb = KnowledgeBase.from_dir(args.docs)
    else:
        kb = KnowledgeBase()
        for name, text in _DEMO_DOCS.items():
            kb.add(name, text)

    try:
        llm = ClaudeLLM()
    except Exception as e:  # noqa: BLE001 — surface any client-init failure plainly
        print(f"Could not initialize Claude client: {e}\n"
              "Set ANTHROPIC_API_KEY or run `ant auth login`.", file=sys.stderr)
        return 2

    reply = draft_reply(args.message, kb, llm)
    if not reply.grounded:
        print("No relevant knowledge found — escalate to a human.")
        return 0

    print(reply.text)
    print(f"\n[sources: {', '.join(reply.citations)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
