#!/usr/bin/env python3
"""Write a canon document, or accept a proposal — the canon plugin's own tool.

    canon_edit.py write  <path>          new text on stdin; bumps `updated:` in the header block
    canon_edit.py accept <path>          replaces the document with <path>.proposal.md, removes the proposal
    canon_edit.py discard <path>         removes <path>.proposal.md

Paths are relative to COCKPIT_DATA_DIR (the canon root). Writes only inside it.
A document keeps its history in git; this tool changes the current text and
nothing else. It never touches a file that is not a .md under the root.
"""
import datetime as dt
import os
import re
import sys
from pathlib import Path

UPDATED = re.compile(r"^(updated:\s*)(.*)$", re.M)


def _target(rel: str) -> Path:
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    p = (root / rel).resolve()
    if not p.is_relative_to(root) or p.suffix != ".md":
        sys.exit(f"'{rel}' is not a canon document under the root")
    return p


def bump_updated(text: str) -> str:
    today = dt.date.today().isoformat()
    if text.startswith("```") and UPDATED.search(text.split("```", 2)[1]):
        head, rest = text.split("```", 2)[1], text.split("```", 2)[2]
        head = UPDATED.sub(lambda m: m.group(1) + today, head, count=1)
        return "```" + head + "```" + rest
    return text


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in ("write", "accept", "discard"):
        sys.exit(__doc__)
    cmd, rel = argv
    p = _target(rel)
    proposal = p.with_suffix(".proposal.md")
    if cmd == "write":
        text = sys.stdin.read()
        if not text.strip():
            sys.exit("empty text — nothing written")
        p.write_text(bump_updated(text if text.endswith("\n") else text + "\n"), encoding="utf-8")
        print(f"written: {rel} ({len(text)} chars)")
    elif cmd == "accept":
        if not proposal.exists():
            sys.exit(f"no proposal for {rel}")
        body = proposal.read_text(encoding="utf-8")
        # the proposal carries a provenance block at the top; keep it out of the canon text
        if body.startswith("<!-- proposal"):
            body = body.split("-->", 1)[1].lstrip("\n")
        p.write_text(bump_updated(body), encoding="utf-8")
        proposal.unlink()
        print(f"accepted proposal for {rel}")
    else:
        if proposal.exists():
            proposal.unlink(); print(f"discarded proposal for {rel}")
        else:
            print(f"no proposal for {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
