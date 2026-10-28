"""Dry run: apply rules.toml to the inboxes of an inventory and show where every message would go.

    python -m mailsort.preview --inventory <dir>

Reads the inventory files only. Writes preview.md next to them. Touches no mailbox.
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from . import rules


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--inventory", required=True, type=Path)
    p.add_argument("--examples", type=int, default=5)
    a = p.parse_args(argv)

    folders, _, fallback = rules.load()
    rows = [json.loads(line) for line in open(a.inventory / "headers.jsonl")]
    inbox = [r for r in rows if r["folder"].upper() == "INBOX"]
    by_target = defaultdict(list)
    for r in inbox:
        by_target[rules.classify(r, folders, fallback).folder].append(r)

    special = (fallback, rules.UNDECIDED)
    n = len(inbox)
    sorted_n = sum(len(v) for k, v in by_target.items() if k not in special)
    out = [f"# Preview — where the inbox backlog would go", "",
           f"{n} messages in the inboxes. Rules only (stage a), no AI, nothing moved.", "",
           "| | Messages | Share |", "|---|---:|---:|",
           f"| sorted by a rule | {sorted_n} | {100 * sorted_n / n:.0f}% |"]
    for k in special:
        out.append(f"| {k} | {len(by_target[k])} | {100 * len(by_target[k]) / n:.0f}% |")

    out += ["", "## By target folder", "", "| Folder | Messages | from accounts |", "|---|---:|---|"]
    for k, v in sorted(by_target.items(), key=lambda kv: -len(kv[1])):
        accs = ", ".join(f"{acc.split('@')[0]} {c}" for acc, c in Counter(r["account"] for r in v).most_common())
        out.append(f"| {k} | {len(v)} | {accs} |")

    for k in special:
        out += ["", f"## {k}: top senders", "", "| Domain | Messages | example subject |", "|---|---:|---|"]
        doms = defaultdict(list)
        for r in by_target[k]:
            doms[r["domain"]].append(r)
        for d, rs in sorted(doms.items(), key=lambda kv: -len(kv[1]))[:40]:
            out.append(f"| {d} | {len(rs)} | {rs[-1]['subject'].replace('|', '/')[:70]} |")

    out += ["", "## Examples per folder", ""]
    for k, v in sorted(by_target.items(), key=lambda kv: -len(kv[1])):
        if k in special:
            continue
        out.append(f"**{k}**")
        for r in v[-a.examples:]:
            out.append(f"- {r['from_name'] or r['from']}: {r['subject'][:80]}")
        out.append("")

    path = a.inventory / "preview.md"
    path.write_text("\n".join(out) + "\n")
    print(path)
    print("\n".join(out[4:9]))


if __name__ == "__main__":
    main()
