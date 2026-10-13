"""The pipeline tools: versioned puts, append-only reviews, honest verification."""

import json
import os
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline"


def run(root, tool, *args, stdin=None):
    return subprocess.run([sys.executable, str(TOOLS / tool), *args], capture_output=True, text=True,
                          env={**os.environ, "COCKPIT_DATA_DIR": str(root)}, input=stdin)


def make(tmp_path):
    (tmp_path / "30-review-human" / "POD-01").mkdir(parents=True)
    (tmp_path / "people.json").write_text(json.dumps({"people": [
        {"id": "chris", "name": "Chris", "kind": "human"}, {"id": "akhil", "name": "Akhil", "kind": "human"},
        {"id": "claude", "name": "Claude", "kind": "agent"}]}))
    (tmp_path / "30-review-human" / "POD-01" / "meta.json").write_text('{"label": "POD", "title": "One"}')
    (tmp_path / "40-asset-generation").mkdir()
    (tmp_path / "up.png").write_bytes(b"\x89PNG fake")
    return tmp_path


def test_put_versions_and_never_overwrites(tmp_path):
    root = make(tmp_path)
    up = root / "up.png"
    r1 = run(root, "asset_put.py", "POD-01", "thumbnail", str(up), "--name", "Akhil final.PNG", "--by", "akhil")
    r2 = run(root, "asset_put.py", "POD-01", "thumbnail", str(up), "--name", "again.png")
    assert r1.returncode == 0 and "thumbnail-16x9.v1.png" in r1.stdout
    assert r2.returncode == 0 and "thumbnail-16x9.v2.png" in r2.stdout and "previous versions: [1]" in r2.stdout
    assert sorted(p.name for p in (root / "30-review-human" / "POD-01").iterdir() if p.name.startswith("thumb")) == ["thumbnail-16x9.v1.png", "thumbnail-16x9.v2.png"]


def test_put_refuses_wrong_type_and_unknown_kind(tmp_path):
    root = make(tmp_path)
    (root / "x.exe").write_bytes(b"MZ")
    assert run(root, "asset_put.py", "POD-01", "thumbnail", str(root / "x.exe"), "--name", "x.exe").returncode != 0
    assert run(root, "asset_put.py", "POD-01", "logo", str(root / "up.png"), "--name", "a.png").returncode != 0
    assert run(root, "asset_put.py", "../etc", "thumbnail", str(root / "up.png"), "--name", "a.png").returncode != 0


def test_review_append_writes_numbered_entries_by_the_schema(tmp_path):
    root = make(tmp_path)
    (root / "review.schema.json").write_text(json.dumps({
        "required": ["id", "date", "author", "status", "title", "text"], "additionalProperties": False,
        "properties": {"id": {"pattern": "^REV-\d{3}$"}, "date": {}, "author": {"enum": ["Chris", "Akhil"]}, "for": {"enum": ["Chris", "Akhil"]},
                       "status": {"enum": ["info", "open", "resolved", "approved"]}, "stage": {}, "title": {}, "resolves": {"pattern": "^REV-\d{3}$"}, "text": {}}}))
    rv = root / "30-review-human" / "POD-01" / "review.md"
    rv.write_text("# Review\n\nOriginal line.\n", encoding="utf-8")
    r = run(root, "review_append.py", "30-review-human/POD-01", "--by", "akhil", "--title", "Thumbnail v2", "--status", "open", "--for", "chris",
            stdin="v2 fixes the crop.")
    assert r.returncode == 0 and r.stdout.startswith("REV-001 appended")
    r = run(root, "review_append.py", "POD-01", "--by", "Chris", "--title", "Take it", "--status", "approved", "--resolves", "rev-001", stdin="Good.")
    assert r.returncode == 0 and "REV-002" in r.stdout and "resolves REV-001" in r.stdout
    text = rv.read_text(encoding="utf-8")
    assert text.startswith("# Review\n\nOriginal line.\n")
    assert "## REV-001 — Thumbnail v2\n**Date:** " in text and "**Author:** Akhil · **For:** Chris · **Status:** open · **Stage:** 30-review-human" in text
    assert "**Status:** approved · **Stage:** 30-review-human · **Resolves:** REV-001" in text

    sys.path.insert(0, str(TOOLS)); import review_entries
    entries = review_entries.parse(text)
    assert [e["id"] for e in entries] == ["REV-001", "REV-002"]
    assert entries[0]["for"] == "Chris" and entries[0]["text"] == "v2 fixes the crop." and entries[1]["resolves"] == "REV-001"
    assert "for" not in entries[1] and review_entries.check(entries[0], review_entries.load_schema(root)) == []

    # refused: a status outside the list, a resolves that does not exist, an empty text
    assert "not one of" in run(root, "review_append.py", "POD-01", "--by", "akhil", "--title", "x", "--status", "maybe", stdin="t").stderr
    assert "not an entry" in run(root, "review_append.py", "POD-01", "--by", "akhil", "--title", "x", "--resolves", "REV-009", stdin="t").stderr
    assert run(root, "review_append.py", "POD-01", "--by", "akhil", "--title", "x", stdin="   ").returncode != 0
    # refused: a person people.json does not know, two persons in For, and nobody at all without the file
    assert "not in people.json" in run(root, "review_append.py", "POD-01", "--by", "nobody", "--title", "x", stdin="t").stderr
    assert "one person" in run(root, "review_append.py", "POD-01", "--by", "akhil", "--for", "Chris, Akhil", "--title", "x", stdin="t").stderr
    (root / "people.json").rename(root / "people.away")
    assert "no people.json" in run(root, "review_append.py", "POD-01", "--by", "akhil", "--title", "x", stdin="t").stderr
    (root / "people.away").rename(root / "people.json")
    assert rv.read_text(encoding="utf-8") == text                      # nothing refused left a trace
    # verify sees an author the list does not know
    rv.write_text(text.replace("**Author:** Chris", "**Author:** Someone"), encoding="utf-8")
    assert "author = 'Someone' is not a name in people.json" in run(root, "verify.py", "POD-01").stdout


def test_verify_finds_duplicates_and_bad_names(tmp_path):
    root = make(tmp_path)
    c = root / "30-review-human" / "POD-01"
    (c / "thumbnail-16x9.v1.png").write_bytes(b"same")
    (c / "Thumbnail FINAL (2).png").write_bytes(b"same")
    r = run(root, "verify.py", "POD-01")
    assert r.returncode == 1 and "duplicate" in r.stdout and "naming" in r.stdout
    (c / "Thumbnail FINAL (2).png").unlink()
    assert run(root, "verify.py", "POD-01").returncode == 0


def test_verify_checks_meta_against_the_schema_and_walks_all(tmp_path):
    root = make(tmp_path)
    (root / "meta.schema.json").write_text(json.dumps({
        "required": ["label", "title"], "additionalProperties": False,
        "properties": {"label": {"enum": ["FN", "POD"]}, "title": {}, "track": {"enum": ["deep-tech"]}}}))
    c = root / "30-review-human" / "POD-01"
    (c / "meta.json").write_text(json.dumps({"label": "EP", "track": "deep-tech", "mood": "x"}))
    r = run(root, "verify.py", "POD-01")
    assert r.returncode == 1
    assert "required field 'title' is missing" in r.stdout and "label = 'EP' is not one of" in r.stdout and "unknown field 'mood'" in r.stdout
    (root / "40-asset-generation" / "POD-02").mkdir()
    r = run(root, "verify.py", "--all")
    assert "40-asset-generation/POD-02: 1" in r.stdout and "meta.json: missing" in r.stdout and "finding(s)" in r.stdout
    (c / "meta.json").write_text(json.dumps({"label": "POD", "title": "ok"}))
    assert run(root, "verify.py", "POD-01").returncode == 0


def test_run_request_queues_and_the_runner_executes_with_a_stub_claude(tmp_path):
    root = make(tmp_path)
    (root / "run.schema.json").write_text((Path(__file__).resolve().parents[1] / "fixtures" / "run.schema.json").read_text())
    (root / "run-policy.json").write_text((Path(__file__).resolve().parents[1] / "fixtures" / "run-policy.json").read_text())
    (root / "review.schema.json").write_text(json.dumps({"required": ["id"], "properties": {
        "id": {}, "date": {}, "author": {}, "for": {}, "status": {"enum": ["info"]}, "stage": {}, "title": {}, "resolves": {}, "text": {}}}))
    r = run(root, "run_request.py", "30-review-human/POD-01", "--skill", "interpret", "--by", "chris", "--role", "operator", "--note", "keep it short")
    assert r.returncode == 0 and "queued" in r.stdout and "1 waiting" in r.stdout
    assert run(root, "run_request.py", "POD-01", "--skill", "dance", "--by", "chris", "--role", "operator").returncode != 0
    # who may order what is the policy's word, not the form's
    r = run(root, "run_request.py", "POD-01", "--skill", "interpret", "--by", "akhil", "--role", "guest")
    assert r.returncode != 0 and "may be ordered by operator, not guest" in r.stderr
    r = run(root, "run_request.py", "POD-01", "--skill", "asset", "--by", "chris", "--role", "operator")
    assert r.returncode != 0 and "not be ordered by anyone" in r.stderr
    assert len(list((root / "_runs").glob("*.json"))) == 1
    order = next((root / "_runs").glob("*.json"))
    data = json.loads(order.read_text())
    assert data["status"] == "queued" and data["skill"] == "interpret" and data["container"] == "30-review-human/POD-01" and data["note"] == "keep it short"
    assert data["requested_by"] == "chris"
    assert "not in people.json" in run(root, "run_request.py", "POD-01", "--skill", "interpret", "--by", "ghost", "--role", "operator").stderr

    # a stand-in for claude: prints the prompt it got, as the json the real one prints
    stub = tmp_path / "claude"
    stub.write_text('#!/bin/sh\nprintf \'{"result": "changed script.v2; open: nothing", "session_id": "s-1", "total_cost_usd": 1.23456, "num_turns": 7, "duration_ms": 4500, '
                    '"modelUsage": {"claude-haiku-4-5": {"costUSD": 0.01}, "claude-opus-5-5": {"costUSD": 1.2}}}\'\n')
    stub.chmod(0o755)
    r = subprocess.run([sys.executable, str(TOOLS / "runner.py"), "--workspace", str(tmp_path), "--data", str(root), "--claude", str(stub), "--once"],
                       capture_output=True, text=True)
    assert r.returncode == 0 and "done" in r.stdout, r.stdout + r.stderr
    data = json.loads(order.read_text())
    assert data["status"] == "done" and data["exit"] == 0 and data["session"] == "s-1" and data["result"].startswith("changed script.v2")
    # the bill travels with the order: dollars, the model that did the work, turns, seconds
    assert data["cost_usd"] == 1.2346 and data["model"] == "claude-opus-5-5" and data["turns"] == 7 and data["duration_s"] == 4.5
    assert (root / "_runs" / (order.stem + ".claim")).is_dir() and (root / "_runs" / (order.stem + ".log")).exists()
    # the session's rights are the policy's lines for this skill, nothing else
    head = (root / "_runs" / (order.stem + ".log")).read_text().splitlines()[1]
    assert f"--add-dir {root}" in head and "--allowedTools Bash(python3:*),Bash(mv:*)" in head and "WebFetch,WebSearch" in head
    assert "--permission-mode acceptEdits" in head and "Bash(git:*)" not in head
    assert "--model claude-opus-5-5" in head                      # the policy's model for interpret
    review = (root / "30-review-human" / "POD-01" / "review.md").read_text()
    assert "## REV-001 — Run /interpret: done" in review and "changed script.v2" in review and "**Author:** Claude" in review
    # without a policy the runner runs nothing, and says so
    (root / "run-policy.json").unlink()
    r = subprocess.run([sys.executable, str(TOOLS / "runner.py"), "--workspace", str(tmp_path), "--data", str(root), "--claude", str(stub), "--once"],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "no run-policy.json" in r.stdout
    (root / "run-policy.json").write_text((Path(__file__).resolve().parents[1] / "fixtures" / "run-policy.json").read_text())
    # a second pass finds nothing queued
    r = subprocess.run([sys.executable, str(TOOLS / "runner.py"), "--workspace", str(tmp_path), "--data", str(root), "--claude", str(stub), "--once"],
                       capture_output=True, text=True)
    assert "taking" not in r.stdout


def test_series_head_clamps_its_pieces_both_ways(tmp_path):
    root = make(tmp_path)
    (root / "series.schema.json").write_text((Path(__file__).resolve().parents[1] / "fixtures" / "series.schema.json").read_text())
    (root / "meta.schema.json").write_text(json.dumps({"properties": {"label": {}, "title": {}, "series": {"type": "string", "x-ref": "series"}, "number": {}}}))
    c = root / "30-review-human" / "POD-01"
    (c / "meta.json").write_text(json.dumps({"label": "POD", "title": "One", "series": "ARC", "number": "ARC-01"}))
    # no head yet: the piece claims a series that does not exist
    assert "has no head" in run(root, "verify.py", "POD-01").stdout
    sd = root / "series" / "ARC"; sd.mkdir(parents=True)
    head = {"label": "ARC", "title": "The Arc", "spine": "One idea, three ways.", "status": "running", "editor": "chris",
            "sourced_by": ["akhil"], "pieces": [{"ref": "FN-ARC-01", "role": "the finding"}, {"ref": "SP-ARC-02", "role": "the hook"}]}
    (sd / "series.json").write_text(json.dumps(head))
    # head exists but does not list this piece; the head's second piece is planned (no folder), which is fine
    r = run(root, "verify.py", "POD-01")
    assert "POD-ARC-01 is not listed in series/ARC/series.json" in r.stdout
    assert run(root, "verify.py", "series/ARC").returncode == 0
    head["pieces"].insert(0, {"ref": "POD-ARC-01", "role": "spoken"})
    (sd / "series.json").write_text(json.dumps(head))
    assert run(root, "verify.py", "POD-01").returncode == 0
    # the head is checked too: a stranger as editor, a ref from another series, a folder name that disagrees
    head["editor"] = "ghost"; head["pieces"].append({"ref": "FN-XYZ-09"})
    (sd / "series.json").write_text(json.dumps(head))
    out = run(root, "verify.py", "series/ARC").stdout
    assert "editor = 'ghost' is not an id in people.json" in out and "FN-XYZ-09 does not carry the series label ARC" in out
    r = run(root, "verify.py", "--all")
    assert "series/ARC:" in r.stdout
    # a series carries a review of its own
    (root / "review.schema.json").write_text(json.dumps({"required": ["id"], "properties": {"id": {}, "date": {}, "author": {}, "for": {}, "status": {"enum": ["info", "open"]}, "stage": {}, "title": {}, "resolves": {}, "text": {}}}))
    r = run(root, "review_append.py", "series/ARC", "--by", "chris", "--title", "Order settled", "--status", "info", stdin="SP last.")
    assert r.returncode == 0 and "REV-001 appended to series/ARC/review.md" in r.stdout
    assert "**Stage:** series" in (sd / "review.md").read_text()


def test_schedule_puts_a_piece_on_a_day_within_the_rhythm(tmp_path):
    root = make(tmp_path)
    (root / "calendar.json").write_text(json.dumps({"slots": ["Mon", "Thu"], "one_per_day": True, "max_gap_days": 4}))
    (root / "60-published" / "SP-001-out").mkdir(parents=True)
    (root / "60-published" / "SP-001-out" / "meta.json").write_text(json.dumps({"label": "SP", "title": "Out", "publishDate": "2026-10-01"}))
    r = run(root, "schedule.py", "30-review-human/POD-01", "2026-10-05")
    assert r.returncode == 0 and "POD-01 planned for 2026-10-05 (Mon)" in r.stdout and "not a slot" not in r.stdout
    assert json.loads((root / "30-review-human" / "POD-01" / "meta.json").read_text())["publishDate"] == "2026-10-05"
    r = run(root, "schedule.py", "POD-01", "2026-10-06")                       # a Tuesday: allowed, noted
    assert r.returncode == 0 and "was 2026-10-05" in r.stdout and "Tue is not a slot" in r.stdout
    assert "one piece per day" in run(root, "schedule.py", "POD-01", "2026-10-01").stderr     # SP-001 holds it
    assert "record now, not a plan" in run(root, "schedule.py", "SP-001-out", "2026-10-09").stderr
    assert "not a date" in run(root, "schedule.py", "POD-01", "next thursday").stderr
    # verify sees two pieces on one day
    (root / "40-asset-generation" / "POD-02").mkdir()
    (root / "40-asset-generation" / "POD-02" / "meta.json").write_text(json.dumps({"label": "POD", "title": "Two", "publishDate": "2026-10-06"}))
    assert "calendar: 2026-10-06 has 2 pieces" in run(root, "verify.py", "--all").stdout


def test_idea_new_writes_a_seed_container_and_refuses_what_the_pipeline_does_not_know(tmp_path):
    root = make(tmp_path)
    (root / "10-ideas").mkdir()
    (root / "meta.schema.json").write_text(json.dumps({
        "required": ["label", "slug", "title"], "additionalProperties": False,
        "properties": {"label": {"enum": ["FN", "POD", "SP", "WN"]}, "slug": {}, "title": {}, "working_title": {},
                       "created": {"pattern": "^\\d{4}-\\d{2}-\\d{2}"}, "origin": {}, "seed": {"type": "boolean"}, "series": {}}}))
    r = run(root, "idea_new.py", "--label", "fn", "--title", "  Über die   Grenze ", "--by", "Akhil", stdin="A process knows its limits.\n")
    assert r.returncode == 0 and r.stdout.strip() == "created 10-ideas/FN-xxx-ueber-die-grenze — FN by Akhil"
    folder = root / "10-ideas" / "FN-xxx-ueber-die-grenze"
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    assert meta["label"] == "FN" and meta["slug"] == folder.name and meta["title"] == "Über die Grenze" and meta["seed"] is True
    assert meta["origin"] == "entered by Akhil in the cockpit" and "series" not in meta
    src = (folder / "source.md").read_text(encoding="utf-8")
    assert src.startswith("# Source — Über die Grenze\n") and "## Core Concept\n\nA process knows its limits." in src
    assert sorted(p.name for p in folder.iterdir()) == ["meta.json", "source.md"]

    # refused: the same title twice, a label outside the list, a stranger, an empty text, a series without a head
    assert "already exists" in run(root, "idea_new.py", "--label", "FN", "--title", "Über die Grenze", "--by", "akhil", stdin="x").stderr
    assert "not one of" in run(root, "idea_new.py", "--label", "DAY", "--title", "Old", "--by", "akhil", stdin="x").stderr
    assert "not in people.json" in run(root, "idea_new.py", "--label", "SP", "--title", "Who", "--by", "nobody", stdin="x").stderr
    assert "text is empty" in run(root, "idea_new.py", "--label", "SP", "--title", "Empty", "--by", "akhil", stdin="  \n").stderr
    assert "has no head" in run(root, "idea_new.py", "--label", "SP", "--title", "Ser", "--by", "akhil", "--series", "SIM", stdin="x").stderr
    assert [p.name for p in (root / "10-ideas").iterdir()] == ["FN-xxx-ueber-die-grenze"]   # nothing refused left a trace

    # a series piece carries the series and takes its place marker instead of xxx
    (root / "series" / "SIM").mkdir(parents=True)
    (root / "series" / "SIM" / "series.json").write_text('{"label": "SIM"}')
    r = run(root, "idea_new.py", "--label", "SP", "--title", "Slot one", "--by", "chris", "--series", "sim", "--text", "inline text")
    assert r.returncode == 0 and "10-ideas/SP-SIM-xx-slot-one" in r.stdout
    assert json.loads((root / "10-ideas" / "SP-SIM-xx-slot-one" / "meta.json").read_text())["series"] == "SIM"


def test_a_piece_may_begin_with_finished_material_and_the_agent_can_be_asked(tmp_path):
    root = make(tmp_path)
    (root / "10-ideas").mkdir()
    (root / "meta.schema.json").write_text(json.dumps({
        "required": ["label", "slug", "title"], "additionalProperties": False,
        "properties": {"label": {"enum": ["FN", "POD", "SP", "WN"]}, "slug": {}, "title": {}, "working_title": {},
                       "created": {}, "origin": {}, "seed": {"type": "boolean"}, "series": {}}}))
    script = root / "akhil-script.md"; script.write_text("# Night shift\n\nThe script, as Akhil wrote it.\n", encoding="utf-8")
    r = run(root, "idea_new.py", "--label", "POD", "--title", "Night shift", "--by", "akhil", "--kind", "script", "--file", str(script), "--name", "Akhil Script.MD")
    assert r.returncode == 0 and "script in script.md" in r.stdout
    c = root / "10-ideas" / "POD-xxx-night-shift"
    assert (c / "script.md").read_text(encoding="utf-8").startswith("# Night shift") and "Begins with:** script" in (c / "source.md").read_text(encoding="utf-8")
    assert "script by Akhil" in json.loads((c / "meta.json").read_text())["origin"]
    # a draft lands under the label's primary name; a script is not a way to begin an essay; a non-text upload is refused
    assert "linkedin-post.txt" in run(root, "idea_new.py", "--label", "SP", "--title", "Short", "--by", "chris", "--kind", "draft", "--text", "The post.").stdout
    assert "not a way to begin" in run(root, "idea_new.py", "--label", "FN", "--title", "Essay", "--by", "chris", "--kind", "script", "--text", "x").stderr
    (root / "x.docx").write_bytes(b"PK")
    assert "not a text file" in run(root, "idea_new.py", "--label", "FN", "--title", "Essay", "--by", "chris", "--kind", "draft", "--file", str(root / "x.docx"), "--name", "x.docx").stderr
    assert "no script given" in run(root, "idea_new.py", "--label", "POD", "--title", "Empty", "--by", "chris", "--kind", "script", "--text", "").stderr

    # asking the agent: one review entry for it, one order with the same words — /derive, because the piece begins with a script
    (root / "run.schema.json").write_text((Path(__file__).resolve().parents[1] / "fixtures" / "run.schema.json").read_text())
    (root / "run-policy.json").write_text((Path(__file__).resolve().parents[1] / "fixtures" / "run-policy.json").read_text())
    (root / "review.schema.json").write_text(json.dumps({"required": ["id"], "properties": {
        "id": {}, "date": {}, "author": {}, "for": {}, "status": {"enum": ["info", "open", "resolved", "approved"]}, "stage": {}, "title": {}, "resolves": {}, "text": {}}}))
    r = run(root, "ask_agent.py", "10-ideas/POD-xxx-night-shift", "--by", "akhil", "--role", "operator", "--title", "Derive the rest", stdin="Teleprompter and show notes, please.")
    assert r.returncode == 0 and r.stdout.startswith("REV-001 appended for Claude, /derive queued"), r.stdout + r.stderr
    assert "**For:** Claude · **Status:** open" in (c / "review.md").read_text(encoding="utf-8")
    order = json.loads(next((root / "_runs").glob("*_derive_POD-xxx-night-shift.json")).read_text())
    assert order["skill"] == "derive" and order["note"].startswith("REV-001 — Derive the rest: Teleprompter")
    # on a piece in review the ask is an /interpret order
    r = run(root, "ask_agent.py", "30-review-human/POD-01", "--by", "chris", "--role", "operator", "--title", "Tighten the opener", stdin="Cut the first paragraph.")
    assert r.returncode == 0 and "/interpret queued" in r.stdout
    assert "say what the agent should do" in run(root, "ask_agent.py", "POD-01", "--by", "chris", "--role", "operator", "--title", "x", stdin=" ").stderr
