#!/usr/bin/env python3
"""The one way in and out of todo.json.

Nothing else writes this file. Every change runs through here, and here every
change is validated against the schema and its references before it is saved —
so a broken list cannot come into being in the first place.

  todo.py list   [--status s] [--assignee p] [--cluster c] [--open] [--due N] [--blocked] [--json]
  todo.py show   ID
  todo.py add    "Titel" --cluster c [--status s] [--prio p] [--assignee a]
                 [--due YYYY-MM-DD] [--blocked-by ID,ID] [--source-kind k] [--source-ref r]
  todo.py set    ID [--status s] [--assignee a] [--prio p] [--due YYYY-MM-DD|-] [--title t]
  todo.py done   ID [--date YYYY-MM-DD]
  todo.py check
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import todo_validate as V

def find_state():
    """Locate todo.json without being told where it is.

    Two layouts must both work and neither may need configuring:
      context/scripts/todo.py  →  context/todo.json        (the shipped package)
      <x>/scripts/todo.py      →  <x>/context/todo.json    (a project that keeps state in context/)
    CONTEXT_LOOP_DIR overrides both when someone puts the files somewhere else.
    """
    import os
    here = Path(__file__).resolve().parent
    candidates = []
    if os.environ.get("CONTEXT_LOOP_DIR"):
        candidates.append(Path(os.environ["CONTEXT_LOOP_DIR"]))
    candidates += [here.parent, here.parent / "context", here]
    for base in candidates:
        if (base / "todo.json").is_file():
            return base
    return candidates[0]


BASE = find_state()
DOC, SCHEMA = BASE / "todo.json", BASE / "todo.schema.json"
TODAY = dt.date.today().isoformat()


def load():
    return json.loads(DOC.read_text(encoding="utf-8"))


def save(doc):
    """Validate, then write. A file that would not pass never reaches the disk."""
    doc["meta"]["updated"] = TODAY
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errs, _ = V.shape(doc, schema)
    refs = V.references(doc)
    if errs or refs:
        for e in errs + refs:
            print("  ABGELEHNT " + e, file=sys.stderr)
        sys.exit("Nicht gespeichert — die Änderung hätte die Liste beschädigt.")
    tmp = DOC.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(DOC)


def lov(doc, name):
    return {e["id"]: e for e in doc["lov"][name]}


def find(doc, tid):
    for t in doc["todos"]:
        if t["id"].upper() == tid.upper():
            return t
    sys.exit(f"Kein Vorgang mit der Nummer {tid}.")


def want(doc, name, value, field):
    if value is None:
        return None
    ids = lov(doc, name)
    if value in ids:
        return value
    by_label = {e.get("label", e.get("name", "")).lower(): i for i, e in ids.items()}
    if value.lower() in by_label:
        return by_label[value.lower()]
    sys.exit(f"'{value}' ist kein gültiger Wert für {field}. Erlaubt: {', '.join(ids)}")


def line(doc, t, width=64):
    cl, st = lov(doc, "clusters"), lov(doc, "statuses")
    pr, pe = lov(doc, "priorities"), lov(doc, "people")
    due = t.get("due") or "—"
    flag = "!" if t.get("due") and t["due"] <= TODAY and t["status"] != "done" else " "
    blocked = (" ⟵ " + ",".join(t["blockedBy"])) if t.get("blockedBy") else ""
    title = t["title"] if len(t["title"]) <= width else t["title"][: width - 1] + "…"
    return (f'{flag}{t["id"]:8} {st[t["status"]]["label"]:9} {pr[t["priority"]]["label"]:8}'
            f' {due:11} {pe[t["assignee"]]["name"].split()[0]:7} {title}{blocked}'
            f'   [{cl[t["cluster"]]["label"]}]')


def cmd_list(a):
    doc = load()
    st, pr = lov(doc, "statuses"), lov(doc, "priorities")
    terminal = {i for i, e in st.items() if e.get("terminal")}
    items = doc["todos"]
    if a.status:
        items = [t for t in items if t["status"] == want(doc, "statuses", a.status, "status")]
    if a.assignee:
        items = [t for t in items if t["assignee"] == want(doc, "people", a.assignee, "assignee")]
    if a.cluster:
        items = [t for t in items if t["cluster"] == want(doc, "clusters", a.cluster, "cluster")]
    if a.open:
        items = [t for t in items if t["status"] not in terminal]
    if a.blocked:
        items = [t for t in items if t.get("blockedBy")]
    if a.due is not None:
        limit = (dt.date.today() + dt.timedelta(days=a.due)).isoformat()
        items = [t for t in items if t.get("due") and t["due"] <= limit and t["status"] not in terminal]
    items.sort(key=lambda t: (t.get("due") or "9999", -pr[t["priority"]]["rank"],
                              st[t["status"]]["order"], t["id"]))
    if a.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return
    for t in items:
        print(line(doc, t))
    print(f"— {len(items)} von {len(doc['todos'])}")


def cmd_show(a):
    doc = load()
    print(json.dumps(find(doc, a.id), ensure_ascii=False, indent=2))


def cmd_add(a):
    doc = load()
    cluster = want(doc, "clusters", a.cluster, "cluster")
    prefix = lov(doc, "clusters")[cluster]["prefix"]
    used = [int(t["id"].rsplit("-", 1)[1]) for t in doc["todos"] if t["id"].startswith(prefix + "-")]
    tid = f"{prefix}-{max(used, default=0) + 1:02d}"
    t = {
        "id": tid, "title": a.title, "cluster": cluster,
        "status": want(doc, "statuses", a.status, "status") or "backlog",
        "priority": want(doc, "priorities", a.prio, "priority") or "medium",
        "assignee": want(doc, "people", a.assignee, "assignee") or doc["meta"]["defaultAssignee"],
        "due": a.due, "created": TODAY, "updated": TODAY,
    }
    if a.blocked_by:
        t["blockedBy"] = [x.strip().upper() for x in a.blocked_by.split(",") if x.strip()]
    t["source"] = {"kind": want(doc, "sourceKinds", a.source_kind, "source.kind") or "decision",
                   "ref": a.source_ref or f"Session {TODAY}", "date": TODAY}
    doc["todos"].append(t)
    save(doc)
    print(line(doc, t))


def cmd_set(a):
    doc = load()
    t = find(doc, a.id)
    before = dict(t)
    if a.status:
        t["status"] = want(doc, "statuses", a.status, "status")
    if a.assignee:
        t["assignee"] = want(doc, "people", a.assignee, "assignee")
    if a.prio:
        t["priority"] = want(doc, "priorities", a.prio, "priority")
    if a.title:
        t["title"] = a.title
    if a.due:
        t["due"] = None if a.due == "-" else a.due
    terminal = {e["id"] for e in doc["lov"]["statuses"] if e.get("terminal")}
    if t["status"] in terminal and not t.get("closed"):
        t["closed"] = TODAY
    if t["status"] not in terminal:
        t.pop("closed", None)
    changed = [k for k in t if before.get(k) != t[k] and k != "updated"]
    if not changed:
        print("nichts geändert")
        return
    t["updated"] = TODAY
    save(doc)
    for k in changed:
        print(f"  {t['id']}.{k}: {before.get(k)!r} → {t[k]!r}")


def cmd_done(a):
    doc = load()
    t = find(doc, a.id)
    t["status"] = "done"
    t["closed"] = a.date or TODAY
    t["updated"] = TODAY
    save(doc)
    print(f"  {t['id']} erledigt am {t['closed']}: {t['title']}")
    waiting = [x["id"] for x in doc["todos"] if t["id"] in x.get("blockedBy", [])]
    if waiting:
        print("  wird frei: " + ", ".join(waiting))


def cmd_check(a):
    sys.exit(V.main(DOC, SCHEMA))


p = argparse.ArgumentParser(prog="todo.py", description=__doc__,
                            formatter_class=argparse.RawDescriptionHelpFormatter)
sub = p.add_subparsers(dest="cmd", required=True)

s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
s.add_argument("--status"); s.add_argument("--assignee"); s.add_argument("--cluster")
s.add_argument("--open", action="store_true"); s.add_argument("--blocked", action="store_true")
s.add_argument("--due", type=int, metavar="N", help="faellig innerhalb von N Tagen")
s.add_argument("--json", action="store_true")

s = sub.add_parser("show"); s.set_defaults(fn=cmd_show); s.add_argument("id")

s = sub.add_parser("add"); s.set_defaults(fn=cmd_add)
s.add_argument("title"); s.add_argument("--cluster", required=True)
s.add_argument("--status"); s.add_argument("--prio"); s.add_argument("--assignee")
s.add_argument("--due"); s.add_argument("--blocked-by")
s.add_argument("--source-kind"); s.add_argument("--source-ref")

s = sub.add_parser("set"); s.set_defaults(fn=cmd_set); s.add_argument("id")
s.add_argument("--status"); s.add_argument("--assignee"); s.add_argument("--prio")
s.add_argument("--due"); s.add_argument("--title")

s = sub.add_parser("done"); s.set_defaults(fn=cmd_done)
s.add_argument("id"); s.add_argument("--date")

sub.add_parser("check").set_defaults(fn=cmd_check)

if __name__ == "__main__":
    a = p.parse_args()
    a.fn(a)
