#!/usr/bin/env python3
"""Rebuild the demo fixtures: a small, invented world.

Run after a demo has been clicked through — the actions write through the
tools for real, so the fixtures drift. `python3 fixtures/make.py` puts them
back. Nothing here comes from a real machine; every name is made up.
"""
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

F = Path(__file__).resolve().parent
today = dt.date.today()
iso = lambda d: d.isoformat()

for d in ("worklist", "flow", "audits", "context-loop", "gatehouse-instance", "home", "plugins", "users.json", ".demo-secret", "canon", "claims"):
    p = F / d
    if p.is_symlink() or p.is_file():
        p.unlink()
    elif p.is_dir():
        shutil.rmtree(p)

# --- work list ----------------------------------------------------------------
wl = F / "home" / "alex" / "context"; wl.mkdir(parents=True)
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
# Two parallel worlds with the same folder mechanics: flow/ (a content pipeline, English) and
# claims/flow/ (a claims assessor, German). Their data lives in world_data.py / world_texts.py.
import struct
import zlib

sys.path.insert(0, str(F)); sys.path.insert(0, str(F.parent))
import world_data                                                            # noqa: E402

nxt = lambda wd, extra=0: today + dt.timedelta(days=((wd - today.weekday()) % 7 or 7) + extra)


class Dates:
    """The dates of a world, all computed from today: the last Mon/Thu slots back, the next two ahead."""
    def __init__(self):
        d, back = today - dt.timedelta(days=1), []
        while len(back) < 16:
            if d.weekday() in (0, 3):
                back.append(iso(d))
            d -= dt.timedelta(days=1)
        self.back = back                                   # back[0] is the newest past slot
        self.nmon, self.nthu = iso(nxt(0)), iso(nxt(3))
        self.nmon_after, self.nthu_after = iso(nxt(0, 7)), iso(nxt(3, 7))

    def ago(self, n):
        return iso(today - dt.timedelta(days=n))

    def stamp(self, days, h, m):
        return f"{iso(today - dt.timedelta(days=days))} {h:02d}:{m:02d}"


_png_cache: dict = {}


def png_bytes(spec: str, w=1200, h=675) -> bytes:
    """A plain gradient with a diagonal band — a stand-in for a thumbnail. Valid PNG, no dependencies."""
    if spec in _png_cache:
        return _png_cache[spec]
    c1, c2 = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in spec.split(":")[1:3])
    rows = []
    for y in range(h):
        t = y / (h - 1)
        base = [c1[k] + (c2[k] - c1[k]) * t for k in range(3)]
        row = bytearray(b"\x00")
        for x in range(w):
            lift = 1.0 + (0.28 if abs(x - 1.1 * y - 380) < 46 else 0.0) + (0.16 if abs(x - 1.1 * y - 520) < 14 else 0.0)
            row += bytes(min(255, int(v * lift)) for v in base)
        rows.append(bytes(row))
    raw = zlib.compress(b"".join(rows), 6)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    out = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")
    _png_cache[spec] = out
    return out


def auto_text(fname: str, title: str, de: bool) -> str:
    """A short, plausible body for a file nobody has to read closely."""
    if de:
        bodies = {
            "substack.md": f"# {title}\n\nKurze Fassung des Gutachtens. Feststellungen, Ursache, Schadenhöhe und offene Punkte sind in der Akte vermerkt.\n",
            "linkedin-post.txt": f"{title}\n\nKurzbericht an den Versicherer: Sachverhalt, Ursache, Schadenhöhe. Einzelheiten im Gutachten.\n",
            "first-comment.txt": "Anschreiben an den Versicherer. Das Gutachten liegt bei.\n",
            "visual-brief.md": "# Fotoauftrag\n\nÜbersicht, Detail und Umgebung des Schadens, jeweils mit Maßstab. Personen und Kennzeichen unkenntlich machen.\n",
            "script.md": f"# Besichtigungsprotokoll - {title}\n\nTermin vor Ort, Feststellungen und Fotos sind notiert.\n",
            "teleprompter.txt": "Gesprächsnotiz für den Rückruf.\n", "show-notes.txt": "Anlagen: Fotos, Messprotokoll.\n",
        }
    else:
        bodies = {
            "substack.md": f"# {title}\n\nA short draft. The point is made in the first paragraph; the rest is evidence.\n",
            "linkedin-post.txt": f"{title}\n\nA short post: the claim in one line, the reason in three, a question at the end.\n",
            "first-comment.txt": "A link to the essay and one extra thought for the comments.\n",
            "visual-brief.md": "# Visual brief\n\nOne strong motif, cool palette, no stock-photo look. Leave room for the title.\n",
            "script.md": f"# {title}\n\nA short script. One idea, told plainly.\n",
            "teleprompter.txt": "The script, cut into breathing lines.\n", "show-notes.txt": "Chapters and links.\n",
        }
    return bodies.get(fname, f"{title}\n")


def write_run(root: Path, container: str, r: dict, now_dt: dt.datetime, agent: str):
    stage, name = container.split("/")
    t0 = now_dt - dt.timedelta(minutes=r["minutes_ago"])
    rid = f"{t0.strftime('%Y%m%d-%H%M%S')}_{r['skill']}_{name}"
    fmt = lambda d: d.isoformat(timespec="seconds")
    run = {"id": rid, "skill": r["skill"], "container": container, "requested_by": r["by"], "runner": "claude-code",
           "status": r["status"], "created": fmt(t0)}
    if r.get("note"):
        run["note"] = r["note"]
    if r["status"] in ("running", "done", "failed"):
        run["started"] = fmt(t0 + dt.timedelta(seconds=20)); run["taken_by"] = "alex@studio"
    if r["status"] in ("done", "failed"):
        dur = r.get("secs") or 90.0
        run["finished"] = fmt(t0 + dt.timedelta(seconds=20 + dur))
        run["exit"] = 0 if r["status"] == "done" else 1
        run["log"] = f"_runs/{rid}.log"
        run["model"] = r["model"]
        run["turns"] = r.get("turns") or 10
        run["duration_s"] = dur
        if r.get("cost") is not None:
            run["cost_usd"] = r["cost"]
        run["result"] = ("Done. The deliverables are in the folder." if r["status"] == "done"
                         else "Stopped: the source material is too thin to interpret. Add a paragraph and run again.")
        log = [f"[{fmt(t0)}] {agent}: starting /{r['skill']} on {container}", f"[{fmt(t0)}] reading source material and the review file"]
        log += ([f"[{fmt(t0 + dt.timedelta(seconds=dur))}] writing deliverables", "result: ok"] if r["status"] == "done"
                else [f"[{fmt(t0 + dt.timedelta(seconds=40))}] error: not enough material to work from", "result: failed (exit 1)"])
        (root / "_runs" / f"{rid}.log").write_text("\n".join(log) + "\n", encoding="utf-8")
    (root / "_runs" / f"{rid}.json").write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


PEOPLE_NOTE = json.loads((F / "people.json").read_text(encoding="utf-8"))["$comment"]


def build_world(flow: Path, W: dict, de: bool):
    from cockpit.plugins.pipeline.review_entries import render             # the one place that knows the entry's shape
    flow.mkdir(parents=True, exist_ok=True)
    for f in ("review.schema.json", "run.schema.json", "series.schema.json", "calendar.json", "run-policy.json"):
        shutil.copy(F / f, flow / f)
    policy = json.loads((F / "run-policy.json").read_text(encoding="utf-8"))
    policy["default"]["agent"] = W["agent"]                               # the headless session signs as the world's agent
    (flow / "run-policy.json").write_text(json.dumps(policy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (flow / "people.json").write_text(json.dumps({"$comment": PEOPLE_NOTE, "people": W["people"]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (flow / "vocabulary.json").write_text(json.dumps(W["vocabulary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (flow / "artifacts.json").write_text(json.dumps(W["artifacts"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if W.get("cover"):
        (flow / "cover.json").write_text(json.dumps(W["cover"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (flow / "meta.schema.json").write_text(json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Container meta (demo)", "type": "object",
        "required": ["label", "title"], "additionalProperties": False,
        "properties": {"label": {"enum": W["meta_labels"]}, "number": {"type": "string"}, "slug": {"type": "string"},
                       "title": {"type": "string"}, "track": {"enum": W["meta_tracks"]},
                       "series": {"type": "string", "x-ref": "series", "description": "The series label — valid when series/<LABEL>/series.json exists."},
                       "publishDate": {"type": ["string", "null"]}, "created": {"type": "string"},
                       "origin": {"type": "string"}, "subtitle": {"type": "string"},
                       "working_title": {"type": "string"}, "seed": {"type": "boolean"}}}, ensure_ascii=False, indent=2) + "\n")
    stages = ["10-ideas", "15-interpretation", "20-produce", "30-review-human", "40-asset-generation", "50-ready-to-publish",
              "55-scheduled", "60-published", "61-field-observation"]
    for s in stages:
        (flow / s).mkdir(exist_ok=True)
    (flow / "_runs").mkdir(exist_ok=True)
    now_dt = dt.datetime.now().astimezone()
    for p in W["pieces"]:
        d = flow / p["stage"] / p["name"]; d.mkdir(parents=True)
        meta = {**p["meta"], "slug": p["name"].lower()}
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for fname, body in p["files"].items():
            if isinstance(body, str) and body.startswith("PNG:"):
                (d / fname).write_bytes(png_bytes(body))
            else:
                (d / fname).write_text(body if body is not None else auto_text(fname, p["meta"]["title"], de), encoding="utf-8")
        if p["review"]:
            text = f"# Review — {p['name']}\n\nAppend only. Newest entry at the end, never edited afterwards.\n"
            for i, e in enumerate(p["review"], 1):
                text += render({"id": f"REV-{i:03d}", "stage": p["stage"], **e})
            (d / "review.md").write_text(text, encoding="utf-8")
        for r in p["runs"]:
            write_run(flow, f"{p['stage']}/{p['name']}", r, now_dt, W["agent"])
    if W.get("placeholders"):                                              # the empty folders the tests rely on, beside the real pieces
        for stage, n in [("10-ideas", 4), ("20-produce", 1), ("30-review-human", 3), ("40-asset-generation", 2), ("50-ready-to-publish", 1),
                         ("60-published", 27), ("61-field-observation", 6), ("70-reference-frames", 1)]:
            for i in range(n):
                (flow / stage / f"piece-{stage[:2]}-{i + 1:02d}").mkdir(parents=True, exist_ok=True)
    for label, head in W["series"].items():
        sd = flow / "series" / label; sd.mkdir(parents=True)
        (sd / "series.json").write_text(json.dumps(head, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (sd / "construct.md").write_text((f"# {head['title']} — Aufbau\n\nWarum diese Fälle, in dieser Reihenfolge.\n" if de
                                          else f"# {head['title']} — construct\n\nWhy these three, in this order.\n"), encoding="utf-8")


D = Dates()
content_world, claims_world = world_data.content(D), world_data.claims(D)
(F / "people.json").write_text(json.dumps({"$comment": PEOPLE_NOTE, "people": content_world["people"]},
                                          ensure_ascii=False, indent=2) + "\n", encoding="utf-8")   # the content world's list, kept beside make.py
build_world(F / "flow", content_world, de=False)
build_world(F / "claims" / "flow", claims_world, de=True)
# the claims world has its own config: same app, other words and path
cfg = (F / "cockpit.demo.toml").read_text(encoding="utf-8")
cfg = (cfg.replace('name = "Cockpit"', 'name = "Schadenakte"').replace('locale = "en"', 'locale = "de"')
       .replace('bind = "127.0.0.1:8200"', 'bind = "127.0.0.1:8301"').replace('path = "flow"', 'path = "claims/flow"')
       .replace('audit = "demo-audit.jsonl"', 'audit = "claims-audit.jsonl"')
       .replace("# Demo: everything below", "# Claims demo (a copy of cockpit.demo.toml, other words): everything below"))
# the claims demo shows one module: the file; the roles name nothing else
import re as _re
_blocks = _re.split(r"(?=^\[\[module\]\])", cfg, flags=_re.M)
_roles = next((b[m.start():] for b in _blocks[1:] if (m := _re.search(r"^\[\[role\]\]", b, _re.M))), "")
_pipeline = next(b[:m.start()] if (m := _re.search(r"^\[\[role\]\]", b, _re.M)) else b for b in _blocks[1:] if _re.search(r'^id = "pipeline"', b, _re.M))
_roles = (_roles.replace('modules = ["worklist", "decisions", "canon", "pipeline", "contextloop"]', 'modules = ["pipeline"]')
                .replace('actions = ["decisions.record", "pipeline.review_append", "pipeline.upload", "pipeline.verify"]', 'actions = ["pipeline.review_append", "pipeline.upload", "pipeline.verify"]'))
cfg = _blocks[0] + _pipeline + _roles
(F / "cockpit.claims.toml").write_text(cfg, encoding="utf-8")

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

# --- gatehouse instance: must match the example pack, so it is derived from it --------
import tomllib
pack = tomllib.loads((F.parent.parent / "gatehouse" / "packs" / "example" / "pack.toml").read_text(encoding="utf-8"))
now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
answers, closed, blocks = {}, [], pack["block"]
for bi, b in enumerate(blocks):
    for qi, q in enumerate(b["question"]):
        qid = q.get("id") or f"{b['id']}.{qi + 1}"
        if bi == 0:
            answers[qid] = {"question_id": qid, "question": q["text"], "text": "An answer given in the room.",
                            "follow_ups": [], "marker": "AS-IS", "answered_at": now}
    if bi == 0:
        closed.append(b["id"])
gh = F / "gatehouse-instance"; gh.mkdir()
(gh / "run.json").write_text(json.dumps({
    "pack_name": pack["pack"]["name"], "pack_version": pack["pack"]["version"], "client": "Northwind Manufacturing",
    "started_at": now, "current_block": blocks[1]["id"], "answers": answers, "closed_blocks": closed},
    ensure_ascii=False, indent=2), encoding="utf-8")
# Let Gatehouse render interview.md itself, so the artifact is the real one, not an imitation.
import sys
sys.path.insert(0, str(F.parent.parent / "gatehouse"))
from gatehouse.instance import Instance, Run, Answer          # noqa: E402
from gatehouse.pack import load as load_pack                  # noqa: E402
_pack = load_pack(F.parent.parent / "gatehouse" / "packs" / "example")
_inst = Instance(gh, _pack)
_inst.save(Run(pack_name=pack["pack"]["name"], pack_version=pack["pack"]["version"], client="Northwind Manufacturing",
               started_at=now, current_block=blocks[1]["id"],
               answers={k: Answer(**v) for k, v in answers.items()}, closed_blocks=closed))
with (gh / "audit.jsonl").open("w", encoding="utf-8") as fh:
    for _ in answers:
        fh.write(json.dumps({"at": now, "event": "model_call", "task": "followup", "destination": "no model attached",
                             "adapter": "echo", "local": True, "egress": False}) + "\n")

# --- a second user with a thinner context, and the decision log for both -------------
sam = F / "home" / "sam" / "context"; sam.mkdir(parents=True)
shutil.copy(wl / "todo.json", sam / "todo.json"); shutil.copy(wl / "todo.schema.json", sam / "todo.schema.json")
for who, entries in (("alex", [
        (today - dt.timedelta(days=40), "Ship the onboarding rewrite before the pricing page", "Onboarding drives the trial; pricing can wait two weeks.", "Doing both in parallel"),
        (today - dt.timedelta(days=12), "Off-site backup goes to a European provider", "Data residency is a contract term with two customers.", "The cheapest US bucket"),
        (today - dt.timedelta(days=3),  "Every vendor login gets its own key", "A shared key cannot be revoked for one party.", "One key, rotated monthly"),
    ]), ("sam", [
        (today - dt.timedelta(days=5), "Case study goes out without customer logos", "Two of three customers asked for anonymity.", "Waiting for all three approvals"),
    ])):
    body = "# Decisions\n\n*One entry per decision, newest at the bottom, never edited afterwards.*\n\n---\n"
    for d, what, why, instead in entries:
        body += f"\n## {iso(d)} — {what}\n**Why:** {why}\n**Instead of:** {instead}\n"
    (F / "home" / who / "context" / "decisions.md").write_text(body, encoding="utf-8")

# --- a small canon: two layers, three documents --------------------------------------
canon = F / "canon"
for rel, typ, purpose, body in (
    ("foundation/principles.md", "principles · canonical", "The rules every domain follows.",
     "# Principles\n\n## 1. A person decides\n\nA model proposes; a person accepts. Nothing enters the rulebook without a name on it.\n\n## 2. Written before built\n\nWhat is not written down is not decided.\n"),
    ("software/review.md", "rule · domain software", "How a change reaches production.",
     "# Review before merge\n\nEvery change is read by a second person before it merges. The reader checks against the specification, not against taste.\n"),
    ("content/voice.md", "rule · domain content", "How the company sounds.",
     "# Voice\n\nShort sentences. One thought per paragraph. No adjectives that do not change a decision.\n"),
):
    p = canon / rel; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"```\npath:        canon/{rel}\ntype:        {typ}\npurpose:     {purpose}\nmaintained:  the owner\nupdated:     {iso(today - dt.timedelta(days=30))}\n```\n\n{body}", encoding="utf-8")

# --- users: password "cockpit-demo" for both -------------------------------------------------
sys.path.insert(0, str(F.parent))
from cockpit.users import Users                              # noqa: E402
u = Users(F / "users.json", F / ".demo-secret")
u.add("alex", "cockpit-demo", "operator", "home/alex/context")      # the display name comes from people.json
u.add("sam", "cockpit-demo", "guest", "home/sam/context")

# --- the Gatehouse plugin, linked from its repo --------------------------------------
from cockpit.plugins import add                              # noqa: E402
add(F.parent.parent / "gatehouse", F / "plugins", link=True)

(F / "demo-audit.jsonl").unlink(missing_ok=True)
(F / "claims-audit.jsonl").unlink(missing_ok=True)
print("fixtures rebuilt: users alex (operator) and sam (guest), password demo")
