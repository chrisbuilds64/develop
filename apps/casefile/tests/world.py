"""A sample pipeline for the tests: an invented content world with a case in every state that matters.

Every name is made up. Built fresh into a temporary directory by the `world` fixture.
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "config" / "pressroom"
STAGES = ["00-archive", "05-operational-observations", "10-ideas", "15-interpretation", "20-produce", "30-review-human",
          "40-asset-generation", "50-ready-to-publish", "55-scheduled", "60-published", "61-field-observation",
          "65-canonical-review", "66-reviewed", "70-reference-frames"]
PEOPLE = {"people": [
    {"id": "chris", "name": "Chris", "kind": "human", "roles": ["author", "approver", "operator"]},
    {"id": "akhil", "name": "Akhil", "kind": "human", "roles": ["visual", "author"]},
    {"id": "sam", "name": "Sam", "kind": "human", "roles": ["approver"], "deputy": None},
    {"id": "axel", "name": "Axel", "kind": "agent", "roles": []},
]}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def entry(n: int, title: str, author: str, status: str = "info", for_: str | None = None, stage: str = "", resolves: str | None = None,
          step: str | None = None, frm: str | None = None, to: str | None = None, files: list[str] | None = None, text: str = "…", when: str = "2026-10-10 10:00") -> str:
    head = [f"**Date:** {when}", f"**Author:** {author}", f"**For:** {for_ or '—'}", f"**Status:** {status}", f"**Stage:** {stage}"]
    if resolves:
        head.append(f"**Resolves:** {resolves}")
    if step:
        head.append(f"**Step:** {step}")
    if frm:
        head.append(f"**From:** {frm}")
    if to:
        head.append(f"**To:** {to}")
    if files:
        head.append(f"**Files:** {', '.join(files)}")
    return f"\n## REV-{n:03d} — {title}\n{' · '.join(head)}\n\n{text}\n"


def build(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    for s in STAGES:
        (root / s).mkdir(exist_ok=True)
    for name in ("artifacts.json", "vocabulary.json", "run-policy.json", "calendar.json"):
        shutil.copy(CONFIG / name, root / name)
    (root / "people.json").write_text(json.dumps(PEOPLE, indent=2))
    cfg = root.parent / "config"
    cfg.mkdir(exist_ok=True)
    stages = json.loads((CONFIG / "stages.json").read_text())
    for st in stages["stages"]:
        for a in st.get("actions", []):
            if a["id"] == "approve_to_visual":
                a["four_eyes"] = True                      # the test world keeps the four-eyes rule on, the pressroom itself does not
    (cfg / "stages.json").write_text(json.dumps(stages, indent=2))
    (cfg / "theme.json").write_text((CONFIG / "theme.json").read_text())
    (root / "_runs").mkdir(exist_ok=True)
    now = dt.datetime(2026, 10, 20, 12, 0)

    def case(stage: str, cid: str, label: str, title: str, files: dict[str, bytes | str] | None = None, review: str = "", meta_extra: dict | None = None):
        d = root / stage / cid
        d.mkdir(parents=True)
        meta = {"label": label, "number": cid.split("-")[1], "title": title, "created": "2026-10-01", **(meta_extra or {})}
        (d / "meta.json").write_text(json.dumps(meta, indent=2))
        for f, content in (files or {}).items():
            (d / f).write_bytes(content if isinstance(content, bytes) else content.encode())
        if review:
            (d / "review.md").write_text(f"# Review — {cid}\n\nAppend only.\n" + review)
        return d

    def run(cid: str, stage: str, skill: str, status: str, minutes_ago: int = 5, **extra):
        when = now - dt.timedelta(minutes=minutes_ago)
        doc = {"id": f"{when.strftime('%Y%m%d-%H%M%S')}_{skill}_{cid}", "skill": skill, "container": f"{stage}/{cid}", "requested_by": "chris",
               "runner": "claude-code", "status": status, "created": when.isoformat(timespec="seconds"), **extra}
        (root / "_runs" / f"{doc['id']}.json").write_text(json.dumps(doc, indent=2))

    # 1 an idea, nobody has touched it
    case("10-ideas", "FN-101-the-quiet-audit", "FN", "The quiet audit", {"source.md": "# idea\n\nthree lines"})
    # 2 an idea with finished material (script) from Akhil
    case("10-ideas", "POD-102-the-handoff", "POD", "The handoff", {"script.md": "# Script\n\nthe whole thing"},
         review=entry(1, "Delivered: script.md", "Akhil", stage="10-ideas", files=["script.md"]))
    # 3 a running helper
    case("15-interpretation", "FN-103-what-the-pilot-taught", "FN", "What the pilot taught us", {"source.md": "x"})
    run("FN-103-what-the-pilot-taught", "15-interpretation", "interpret", "running", started=(now - dt.timedelta(minutes=4)).isoformat(timespec="seconds"))
    # 4 a failed run
    case("10-ideas", "WN-104-notes-on-friction", "WN", "Notes on friction", {"source.md": "x"})
    run("WN-104-notes-on-friction", "10-ideas", "interpret", "failed", minutes_ago=30, finished=(now - dt.timedelta(minutes=25)).isoformat(timespec="seconds"), log="_runs/x.log", exit=1)
    # 5 a draft in review, written by the agent, nothing open → Chris approves
    case("30-review-human", "FN-105-the-review-that-reads-itself", "FN", "The review that reads itself",
         {"substack.md": "# Draft\n\n400 words", "linkedin-post.txt": "post", "first-comment.txt": "c", "visual-brief.md": "b", "validation.md": "v"},
         review=entry(1, "Interpretation done", "Axel", stage="30-review-human", files=["substack.md", "linkedin-post.txt"], to="30-review-human", frm="20-produce"))
    run("FN-105-the-review-that-reads-itself", "30-review-human", "interpret", "done", minutes_ago=600, cost_usd=2.4)
    # 6 a draft in review with an open note to Chris from the agent
    case("30-review-human", "FN-106-two-models-agreeing", "FN", "Two models agreeing", {"substack.md": "# Draft"},
         review=entry(1, "Draft ready", "Axel", stage="30-review-human", files=["substack.md"]) +
                entry(2, "Which title?", "Axel", status="open", for_="Chris", stage="30-review-human", text="A or B?") +
                entry(3, "Also: the date", "Axel", status="open", for_="Akhil", stage="30-review-human"))
    # 7 a draft in review where the only approver wrote the draft (four eyes)
    case("30-review-human", "SP-107-written-by-chris", "SP", "Written by Chris", {"linkedin-post.txt": "post"},
         review=entry(1, "Delivered: linkedin-post.txt", "Chris", stage="30-review-human", files=["linkedin-post.txt"]))
    # 8 a draft in review whose primary is missing
    case("30-review-human", "FN-108-missing-draft", "FN", "Missing draft", {"visual-brief.md": "b"})
    # 9 in visual, no image yet → Akhil delivers
    case("40-asset-generation", "SP-109-the-intern", "SP", "The intern that never sleeps", {"linkedin-post.txt": "post"},
         review=entry(1, "Approved", "Chris", status="approved", stage="30-review-human", step="s-109", frm="30-review-human", to="40-asset-generation"))
    # 10 in visual, image present → Chris approves the visual
    case("40-asset-generation", "POD-110-the-silent-failure", "POD", "The silent failure", {"script.md": "s", "thumbnail-16x9.png": PNG},
         review=entry(1, "Approved", "Chris", status="approved", stage="30-review-human", step="s-110", frm="30-review-human", to="40-asset-generation") +
                entry(2, "Delivered: thumbnail-16x9.png", "Akhil", stage="40-asset-generation", files=["thumbnail-16x9.png"]))
    # 11 ready, pick a date
    case("50-ready-to-publish", "FN-111-the-boring-win", "FN", "The boring governance win", {"substack.md": "d", "header-16x9.png": PNG})
    # 12 scheduled
    case("55-scheduled", "SP-112-the-handover-note", "SP", "The handover note", {"linkedin-post.txt": "p", "linkedin-image.png": PNG}, meta_extra={"publishDate": "2026-10-22"})
    # 13 published
    case("60-published", "FN-113-the-first-arc", "FN", "The first arc", {"substack.md": "d"}, meta_extra={"publishDate": "2026-09-24"})
    # 14 in field observation
    case("61-field-observation", "SP-114-one-file-per-decision", "SP", "One file per decision", {"linkedin-post.txt": "p"}, meta_extra={"publishDate": "2026-09-17"})
    # 15 being produced (claude's move, no run file at all)
    case("20-produce", "SP-115-the-fourth-reviewer", "SP", "The fourth reviewer", {"source.md": "x"})
    # 16 moved by hand: the thread says 30, the folder says 40
    case("40-asset-generation", "FN-116-moved-by-hand", "FN", "Moved by hand", {"substack.md": "d"},
         review=entry(1, "Draft ready", "Axel", stage="30-review-human", files=["substack.md"]))
    # 17 an observation
    case("05-operational-observations", "OBS-117-a-signal", "FN", "A signal", {"source.md": "x"})
    # 18 archived
    case("00-archive", "FN-118-old", "FN", "Old", {"substack.md": "d"})
    # 19 a review case where Sam (second approver) exists: the primary by the agent, so both may approve
    case("30-review-human", "WN-119-weekend", "WN", "A weekend note", {"substack.md": "d"},
         review=entry(1, "Draft ready", "Axel", stage="30-review-human", files=["substack.md"]))
    return root
