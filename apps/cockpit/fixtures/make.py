#!/usr/bin/env python3
"""Rebuild the demo fixtures: a small, invented world.

Run after a demo has been clicked through — the actions write through the
tools for real, so the fixtures drift. `python3 fixtures/make.py` puts them
back. Nothing here comes from a real machine; every name is made up.
"""
import datetime as dt
import json
import shutil
from pathlib import Path

F = Path(__file__).resolve().parent
today = dt.date.today()
iso = lambda d: d.isoformat()

for d in ("worklist", "flow", "audits", "context-loop", "gatehouse-instance"):
    shutil.rmtree(F / d, ignore_errors=True)

# --- work list ----------------------------------------------------------------
wl = F / "worklist"; wl.mkdir()
lov = {
    "clusters":   [{"id": "product", "label": "Product", "order": 1, "prefix": "PRD"},
                   {"id": "ops", "label": "Operations", "order": 2, "prefix": "OPS"},
                   {"id": "sales", "label": "Sales", "order": 3, "prefix": "SLS"}],
    "statuses":   [{"id": "next", "label": "Next", "order": 1}, {"id": "doing", "label": "Doing", "order": 2},
                   {"id": "waiting", "label": "Waiting", "order": 3}, {"id": "backlog", "label": "Backlog", "order": 4},
                   {"id": "done", "label": "Done", "order": 5, "terminal": True}],
    "priorities": [{"id": "high", "label": "high", "rank": 3}, {"id": "medium", "label": "medium", "rank": 2},
                   {"id": "low", "label": "low", "rank": 1}],
    "people":     [{"id": "me", "name": "Alex Rivera", "kind": "human"}, {"id": "vendor", "name": "Vendor", "kind": "external"}],
    "sourceKinds": [{"id": "session", "label": "Session"}, {"id": "audit", "label": "Audit"},
                    {"id": "decision", "label": "Decision"}, {"id": "other", "label": "Other"}],
}
rows = [
    ("PRD-01", "Ship the onboarding rewrite", "doing", "high", "me", iso(today + dt.timedelta(days=3)), None, []),
    ("PRD-02", "Migrate the pricing page", "next", "high", "me", iso(today + dt.timedelta(days=6)), None, []),
    ("PRD-03", "Retire the legacy export", "backlog", "medium", "me", None, None, []),
    ("OPS-01", "Rotate the API keys", "next", "high", "me", iso(today - dt.timedelta(days=2)), None, []),
    ("OPS-02", "Restore test after the backup change", "waiting", "high", "vendor", None, None, ["OPS-03"]),
    ("OPS-03", "Book the off-site backup", "doing", "high", "me", None, None, []),
    ("OPS-04", "Document the deploy runbook", "backlog", "low", "me", None, None, []),
    ("SLS-01", "Send the proposal to Northwind", "done", "high", "me", None, iso(today - dt.timedelta(days=2)), []),
    ("SLS-02", "Prepare the Q4 demo", "next", "medium", "me", iso(today + dt.timedelta(days=12)), None, []),
    ("SLS-03", "Follow up with the pilot customer", "waiting", "medium", "vendor", None, None, []),
    ("SLS-04", "Draft the case study", "done", "medium", "me", None, iso(today - dt.timedelta(days=5)), []),
]
todos = []
for tid, title, status, prio, who, due, closed, blocked in rows:
    t = {"id": tid, "title": title, "cluster": {"PRD": "product", "OPS": "ops", "SLS": "sales"}[tid[:3]],
         "status": status, "priority": prio, "assignee": who, "due": due,
         "created": iso(today - dt.timedelta(days=20)), "updated": iso(today - dt.timedelta(days=1)),
         "source": {"kind": "session", "ref": "demo"}}
    if closed:
        t["closed"] = closed
    if blocked:
        t["blockedBy"] = blocked
    todos.append(t)
(wl / "todo.json").write_text(json.dumps({
    "$schema": "./todo.schema.json", "schemaVersion": 1,
    "meta": {"title": "Work list", "updated": iso(today), "defaultAssignee": "me"},
    "lov": lov, "todos": todos}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
# todo.py validates against the schema beside the file before it saves — it must be there.
shutil.copy(F / "tools" / "todo.schema.json", wl / "todo.schema.json")

# --- content pipeline ---------------------------------------------------------
flow = F / "flow"
for stage, n in [("10-ideas", 4), ("20-produce", 1), ("30-review-human", 3), ("40-asset-generation", 2),
                 ("50-ready-to-publish", 1), ("60-published", 27), ("61-field-observation", 6),
                 ("70-reference-frames", 1)]:
    for i in range(n):
        (flow / stage / f"piece-{stage[:2]}-{i + 1:02d}").mkdir(parents=True)

# --- audits -------------------------------------------------------------------
au = F / "audits"; au.mkdir()
for d, k in [(today - dt.timedelta(days=9), "security"), (today - dt.timedelta(days=9), "documentation"),
             (today - dt.timedelta(days=23), "security"), (today - dt.timedelta(days=23), "documentation")]:
    (au / f"{iso(d)}_{k}-audit.md").write_text(f"# {k} audit {d}\n", encoding="utf-8")

# --- context loop -------------------------------------------------------------
cl = F / "context-loop"; (cl / ".claude-plugin").mkdir(parents=True)
(cl / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "context-loop", "version": "1.0.0"}, indent=2),
                                                   encoding="utf-8")
for s in ["session-start", "session-end", "observe", "todo", "todo-add", "todo-done",
          "new-agent", "security-audit", "doc-audit"]:
    (cl / "skills" / s).mkdir(parents=True)
    (cl / "skills" / s / "SKILL.md").write_text(f"# {s}\n", encoding="utf-8")

# --- gatehouse instance -------------------------------------------------------
gh = F / "gatehouse-instance"; gh.mkdir()
answers = {f"q{i}": {"question_id": f"q{i}", "question": f"Question {i}", "text": "An answer." if i <= 42 else "",
                     "follow_ups": [], "marker": "AS-IS", "answered_at": iso(today)} for i in range(1, 56)}
(gh / "run.json").write_text(json.dumps({
    "pack_name": "core-de", "pack_version": "0.3", "client": "Northwind Manufacturing",
    "started_at": f"{iso(today - dt.timedelta(days=1))}T09:30:00+02:00", "current_block": "b5",
    "answers": answers, "closed_blocks": ["b1", "b2", "b3", "b4"]}, ensure_ascii=False, indent=2), encoding="utf-8")
with (gh / "audit.jsonl").open("w", encoding="utf-8") as fh:
    for i in range(84):
        fh.write(json.dumps({"at": f"{iso(today)}T10:{i % 60:02d}:00+00:00", "event": "model_call", "task": "followup",
                             "destination": "Ollama" if i % 3 else "Anthropic API", "egress": i % 3 == 0}) + "\n")

(F / "demo-audit.jsonl").unlink(missing_ok=True)
print("fixtures rebuilt")
