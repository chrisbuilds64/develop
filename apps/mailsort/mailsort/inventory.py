"""Stage 0: read-only inventory of every configured mailbox.

For each account: every folder with its count; the full inbox (the backlog); the last 30 days in
every folder (the inflow); and the newest messages of every other folder (what the existing rules
sort where). Writes raw headers as JSONL and a report. Changes nothing in any mailbox.

    python -m mailsort.inventory --out <dir>
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import config, imap

SKIP_FLAGS = ("\\Noselect", "\\NonExistent")
SPECIAL = ("\\Sent", "\\Drafts", "\\Trash", "\\Junk", "\\All")


def is_bulk(h: dict) -> bool:
    return bool(h["list_id"] or h["unsubscribe"] or h["precedence"] in ("bulk", "list", "junk")
                or (h["auto_submitted"] and h["auto_submitted"] != "no"))


def scan(account, since: date, per_folder: int, log):
    rows, folder_counts = [], []
    with imap.connect(account) as conn:
        for f in imap.folders(conn):
            if any(fl in f["flags"] for fl in SKIP_FLAGS):
                continue
            count = imap.select(conn, f["raw"])
            if count is None:
                log(f"  ! {f['name']}: not selectable")
                continue
            special = next((s for s in SPECIAL if s in f["flags"]), "")
            folder_counts.append({"account": account.address, "folder": f["name"], "count": count, "special": special})
            if count == 0:
                continue
            is_inbox = f["name"].upper() == "INBOX"
            uids = imap.all_uids(conn)
            picked = set()
            if is_inbox:
                picked.update(uids)
            elif not special:
                picked.update(uids[-per_folder:])
            picked.update(imap.search_uids(conn, f'SINCE {since.strftime("%d-%b-%Y")}'))
            picked = sorted(picked, key=int)
            log(f"  {f['name']}: {count} messages, reading {len(picked)} headers")
            for uid, h in imap.fetch_headers(conn, picked):
                rows.append({"account": account.address, "folder": f["name"], "special": special, "uid": uid, **h})
    return rows, folder_counts


def _since(h, cutoff):
    if not h["date"]:
        return False
    try:
        d = datetime.fromisoformat(h["date"])
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d >= cutoff
    except ValueError:
        return False


def report(rows, folder_counts, days: int, target: str) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = [f"# Mail inventory {date.today().isoformat()}", "",
           f"Read-only. {len(rows)} headers read. Inflow window: last {days} days.", ""]

    out += ["## Accounts", "", "| Account | Folders | Messages | Inbox | Inflow (all folders, window) | per day |",
            "|---|---:|---:|---:|---:|---:|"]
    by_acc = defaultdict(list)
    for r in rows:
        by_acc[r["account"]].append(r)
    for acc in dict.fromkeys(c["account"] for c in folder_counts):
        fc = [c for c in folder_counts if c["account"] == acc]
        inbox = next((c["count"] for c in fc if c["folder"].upper() == "INBOX"), 0)
        recent = [r for r in by_acc[acc] if _since(r, cutoff) and r["special"] not in ("\\Sent", "\\Drafts")]
        recent_ids = {r["message_id"] or (r["folder"], r["uid"]) for r in recent}
        out.append(f"| {acc} | {len(fc)} | {sum(c['count'] for c in fc)} | {inbox} | {len(recent_ids)} | "
                   f"{len(recent_ids) / days:.1f} |")

    inbox_rows = [r for r in rows if r["folder"].upper() == "INBOX"]
    out += ["", "## Backlog: inboxes", "", f"{len(inbox_rows)} messages, "
            f"{sum(is_bulk(r) for r in inbox_rows)} carry list/bulk/auto headers.", "",
            "### Age", "", "| Month | Messages |", "|---|---:|"]
    months = Counter((r["date"] or "unknown")[:7] for r in inbox_rows)
    for m, n in sorted(months.items(), reverse=True):
        out.append(f"| {m} | {n} |")

    out += ["", "### Top sender domains in the inboxes", "", "| Domain | Messages | bulk | example subject |",
            "|---|---:|---:|---|"]
    doms = defaultdict(list)
    for r in inbox_rows:
        doms[r["domain"]].append(r)
    for d, rs in sorted(doms.items(), key=lambda kv: -len(kv[1]))[:40]:
        subj = rs[-1]["subject"].replace("|", "/")[:70]
        out.append(f"| {d} | {len(rs)} | {sum(is_bulk(r) for r in rs)} | {subj} |")

    out += ["", "### Inbox by receiving address", "", "| Address | Messages |", "|---|---:|"]
    own = {a for a in by_acc}
    rc = Counter(next((a for a in r["rcpt"] if a in own), r["account"]) for r in inbox_rows)
    for a, n in rc.most_common():
        out.append(f"| {a} | {n} |")

    out += ["", f"## Existing sorting in {target}", "",
            "Folders as the current rules left them. Top senders per folder are candidate rules.", "",
            "| Folder | Messages | top domains (in sample) | bulk share |", "|---|---:|---|---:|"]
    for c in sorted((c for c in folder_counts if c["account"] == target and c["folder"].upper() != "INBOX"
                     and not c["special"]), key=lambda c: c["folder"]):
        rs = [r for r in by_acc[target] if r["folder"] == c["folder"]]
        top = ", ".join(f"{d} ({n})" for d, n in Counter(r["domain"] for r in rs).most_common(4))
        share = f"{100 * sum(is_bulk(r) for r in rs) / len(rs):.0f}%" if rs else "—"
        out.append(f"| {c['folder']} | {c['count']} | {top} | {share} |")

    out += ["", "## Other folders (non-target accounts)", "", "| Account | Folder | Messages |", "|---|---|---:|"]
    for c in folder_counts:
        if c["account"] != target and c["folder"].upper() != "INBOX":
            out.append(f"| {c['account']} | {c['folder']} | {c['count']} |")
    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", required=True, type=Path, help="output directory (private, never a repo)")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--per-folder", type=int, default=100, help="newest messages read per sorted folder")
    p.add_argument("--account", action="append", help="limit to these addresses")
    a = p.parse_args(argv)

    target, accounts = config.load()
    if a.account:
        accounts = [x for x in accounts if x.address in a.account]
    since = date.today() - timedelta(days=a.days)
    a.out.mkdir(parents=True, exist_ok=True)
    log = lambda s: print(s, file=sys.stderr, flush=True)

    rows, counts = [], []
    for acc in accounts:
        log(f"{acc.address}")
        r, c = scan(acc, since, a.per_folder, log)
        rows += r
        counts += c

    with open(a.out / "headers.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (a.out / "folders.json").write_text(json.dumps(counts, ensure_ascii=False, indent=1))
    (a.out / "report.md").write_text(report(rows, counts, a.days, target))
    log(f"written: {a.out}/report.md")


if __name__ == "__main__":
    main()
