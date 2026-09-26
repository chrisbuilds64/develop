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


def test_review_append_only_appends(tmp_path):
    root = make(tmp_path)
    rv = root / "30-review-human" / "POD-01" / "review.md"
    rv.write_text("# Review\n\nOriginal line.\n", encoding="utf-8")
    r = run(root, "review_append.py", "POD-01", "--by", "akhil", stdin="Thumbnail v2 fixes the crop.")
    assert r.returncode == 0
    text = rv.read_text(encoding="utf-8")
    assert text.startswith("# Review\n\nOriginal line.\n") and "— akhil · in `30-review-human`" in text
    assert text.rstrip().endswith("Thumbnail v2 fixes the crop.")
    assert run(root, "review_append.py", "POD-01", "--by", "akhil", stdin="   ").returncode != 0


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
    assert "required field 'title' is missing" in r.stdout and "label = 'EP' is not one of" in r.stdout and "'mood' is not in the schema" in r.stdout
    (root / "40-asset-generation" / "POD-02").mkdir()
    r = run(root, "verify.py", "--all")
    assert "40-asset-generation/POD-02: 1" in r.stdout and "meta.json: missing" in r.stdout and "finding(s)" in r.stdout
    (c / "meta.json").write_text(json.dumps({"label": "POD", "title": "ok"}))
    assert run(root, "verify.py", "POD-01").returncode == 0
