#!/usr/bin/env python3
"""Ask a model to improve a canon document — and write a proposal, never the document.

    canon_ask.py <path> --ask "<instruction>" [--model claude-sonnet-5]

The document and the instruction go to the model; the answer is written to
<path>.proposal.md with a provenance block (model, time, instruction). A
person accepts or discards it in the cockpit. The API key comes from the
environment (ANTHROPIC_API_KEY), never from a file this tool reads. Every
call is one line in COCKPIT_DATA_DIR/.canon-ask.jsonl, before it is sent.
"""
import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

PROMPT = """You are helping revise one document of a company's canon — its rulebook.
Return the complete revised document in the same format (keep the header block
between ``` fences unchanged except nothing; keep headings). Change only what the
instruction asks for; keep the author's voice. Return the document text only, no
commentary before or after.

Instruction: {ask}

Document:
{doc}"""


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="canon_ask.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("path"); p.add_argument("--ask", required=True); p.add_argument("--model", default="claude-sonnet-5")
    a = p.parse_args(argv)
    root = Path(os.environ.get("COCKPIT_DATA_DIR") or ".").resolve()
    doc = (root / a.path).resolve()
    if not doc.is_relative_to(root) or doc.suffix != ".md" or not doc.is_file():
        sys.exit(f"'{a.path}' is not a canon document under the root")
    if not a.ask.strip():
        sys.exit("the instruction is empty")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY is not set — start the cockpit with the key in its environment")
    try:
        import anthropic
    except ImportError:
        sys.exit("the anthropic package is not installed in this environment")

    text = doc.read_text(encoding="utf-8")
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    with (root / ".canon-ask.jsonl").open("a", encoding="utf-8") as fh:      # before it is sent
        fh.write(json.dumps({"at": now, "doc": a.path, "model": a.model, "ask": a.ask, "chars": len(text)}) + "\n")

    client = anthropic.Anthropic()
    msg = client.messages.create(model=a.model, max_tokens=8000,
                                 messages=[{"role": "user", "content": PROMPT.format(ask=a.ask, doc=text)}])
    if msg.stop_reason == "max_tokens":
        sys.exit("the answer was cut off — no proposal written")
    out = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    if not out:
        sys.exit("empty answer — no proposal written")
    if out.startswith("```markdown"):
        out = out.split("\n", 1)[1].rsplit("```", 1)[0]
    provenance = f"<!-- proposal · model {msg.model} · {now} · instruction: {a.ask.replace('-->', '')} -->\n"
    doc.with_suffix(".proposal.md").write_text(provenance + out.rstrip() + "\n", encoding="utf-8")
    print(f"proposal written: {a.path}.proposal.md — model {msg.model}, {len(out)} chars. Read it, then accept or discard.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
