"""Derive a first rules.toml from an inventory: every sorted folder whose senders are clean becomes a rule.

    python -m mailsort.bootstrap --inventory <dir> --root <prefix> [--out ~/.config/mailsort/rules.toml]

A domain becomes a rule for a folder when at least --purity of its sampled messages sit in that folder.
Generic mail providers and the owner's own domains never become rules. The result is a draft for a
person to review, not a decision.
"""

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .inventory import is_bulk

GENERIC = {"gmail.com", "googlemail.com", "icloud.com", "me.com", "mac.com", "hotmail.de", "hotmail.com",
           "outlook.com", "gmx.de", "gmx.net", "web.de", "yahoo.com", "t-online.de"}

ACTION_FOLDERS = [
    {"path": "_Handeln", "kind": "action",
     "hint": "A person expects something from me: a question, a request, a deadline, a decision. "
             "Personal or business mail written by a human, not a newsletter."},
    {"path": "_Belege", "kind": "action",
     "hint": "Invoices, receipts, payment confirmations, account statements, booking confirmations.",
     "subject": ["rechnung", "invoice", "receipt", "quittung", "beleg", "zahlungsbestätigung",
                 "payment", "kontoauszug", "buchungsbestätigung"]},
    {"path": "_Benachrichtigungen", "kind": "action",
     "hint": "Machine-generated notices: security alerts, logins, CI and repository activity, "
             "shipping status, system and service messages. Not marketing.",
     "domains": ["github.com", "accounts.google.com"]},
]


def q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def derive(rows, target: str, purity: float, own: set[str], root: str):
    dom_folders = defaultdict(Counter)
    folder_rows = defaultdict(list)
    for r in rows:
        if (r["account"] == target and r["folder"].startswith(root) and r["domain"]
                and not r["folder"].lower().endswith("/_archive")):
            dom_folders[r["domain"]][r["folder"]] += 1
            folder_rows[r["folder"]].append(r)
    rules = defaultdict(list)
    for d, c in dom_folders.items():
        if d in GENERIC or any(d == o or d.endswith("." + o) for o in own):
            continue
        folder, n = c.most_common(1)[0]
        if n / sum(c.values()) >= purity:
            rules[folder].append(d)
    out = []
    for folder in sorted(rules):
        rs = folder_rows[folder]
        bulk = sum(is_bulk(r) for r in rs) / len(rs)
        kind = "newsletter" if bulk >= 0.8 else "source"
        name = folder.rsplit("/", 1)[-1]
        hint = (f"Newsletter/community mail from {name}. Kept to read now and then, never urgent."
                if kind == "newsletter" else f"Mail from {name}. Grouped by source.")
        out.append({"path": folder, "kind": kind, "hint": hint, "domains": sorted(rules[folder]),
                    "sample": len(rs)})
    return out


def render(folders, target: str) -> str:
    lines = [
        f"# mailsort rules — draft derived from the inventory on {date.today().isoformat()}.",
        "# Review and edit freely; this file is the rulebook. Folders live in the target account.",
        "#   kind: newsletter | source | action",
        "#   domains: sender domain or any subdomain of it",
        "#   hint: what the AI reads when no rule matches",
        "",
        f"target = {q(target)}",
        "",
        "[privacy]",
        "# Senders and domains that never reach the AI (customers, private people). Undecided mail stays in the inbox.",
        "never_ai = []",
        "",
    ]
    for f in ACTION_FOLDERS + folders:
        lines.append("[[folder]]")
        lines.append(f"path = {q(f['path'])}")
        lines.append(f"kind = {q(f['kind'])}")
        lines.append(f"hint = {q(f['hint'])}")
        for key in ("domains", "subject"):
            if f.get(key):
                lines.append(f"{key} = [{', '.join(q(x) for x in f[key])}]")
        if "sample" in f:
            lines.append(f"# derived from {f['sample']} sampled messages")
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--inventory", required=True, type=Path)
    p.add_argument("--out", type=Path, default=Path("~/.config/mailsort/rules.toml").expanduser())
    p.add_argument("--root", required=True, help="folder prefix the existing sorting lives under, e.g. Sorted/")
    p.add_argument("--purity", type=float, default=0.9)
    p.add_argument("--force", action="store_true", help="overwrite an existing rules file")
    a = p.parse_args(argv)

    from . import config
    target, accounts = config.load()
    own = {acc.address.rsplit("@", 1)[1] for acc in accounts} - GENERIC
    rows = [json.loads(line) for line in open(a.inventory / "headers.jsonl")]
    folders = derive(rows, target, a.purity, own, a.root)
    if a.out.exists() and not a.force:
        raise SystemExit(f"{a.out} exists; pass --force to overwrite")
    a.out.write_text(render(folders, target))
    kinds = Counter(f["kind"] for f in folders)
    print(f"{a.out}: {len(folders)} folders ({dict(kinds)}), "
          f"{sum(len(f['domains']) for f in folders)} domains, plus {len(ACTION_FOLDERS)} action folders")


if __name__ == "__main__":
    main()
