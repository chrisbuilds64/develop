"""The design guard (tools/design_guard.py): the repository stays within its baseline, and a raw value outside the tokens fails."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("design_guard", REPO / "tools" / "design_guard.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def tree(tmp: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp


def test_the_repository_is_within_its_baseline():
    assert guard.over(guard.scan(), guard.load_baseline()) == []


def test_a_raw_colour_in_a_new_file_fails(tmp_path):
    root = tree(tmp_path, {"apps/casefile/web/src/new.css": ".x { color: #1D4ED8; }\n"})
    msgs = guard.over(guard.scan(root), {})
    assert msgs and "new.css: colour 1 > 0" in msgs[0]


def test_tokens_comments_and_the_tokens_file_pass(tmp_path):
    root = tree(tmp_path, {
        "apps/casefile/web/src/tokens.css": ":root { --ink: #1B1916; --r-s: 8px; }\n",
        "apps/casefile/web/src/ok.css": "/* the accent (#1D4ED8) */\n.x { color: var(--ink); font-family: var(--mono); border-radius: var(--r-s); }\n.y { border-radius: 50%; }\n",
        "apps/casefile/web/src/Ok.tsx": "// colour #fff is the token's job\nexport const A = () => <b style={{ color: \"var(--ink)\" }} />;\n",
    })
    assert guard.scan(root) == {}


def test_each_rule_is_seen(tmp_path):
    root = tree(tmp_path, {"apps/cockpit/cockpit/static/raw.css": ".a { color: rgb(1,2,3); font-size: 13px; font-family: Inter; border-radius: 6px; }\n"})
    assert set(guard.scan(root)["apps/cockpit/cockpit/static/raw.css"]) == {"colour", "font-size", "font-family", "radius"}


def test_the_baseline_only_goes_down(tmp_path):
    root = tree(tmp_path, {"apps/casefile/web/src/a.css": ".a { color: #000; }\n"})
    path = tmp_path / "baseline.json"
    assert guard.write_baseline(guard.scan(root), {}, accept_more=False, path=path) == ["apps/casefile/web/src/a.css: colour 1 > 0"]
    assert not path.exists()
    assert guard.write_baseline(guard.scan(root), {}, accept_more=True, path=path) == []
    assert json.loads(path.read_text())["files"] == {"apps/casefile/web/src/a.css": {"colour": 1}}
    (root / "apps/casefile/web/src/a.css").write_text(".a { color: var(--ink); }\n")
    assert guard.write_baseline(guard.scan(root), guard.load_baseline(path), accept_more=False, path=path) == []
    assert guard.load_baseline(path) == {}
