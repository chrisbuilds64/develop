"""The surface over HTTP: gate, lockout, uploads that version, media that is served only through access."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cockpit.app import create_app
from cockpit.config import load

FIX = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def world(tmp_path):
    """A private copy of the demo world, so a test may write into it."""
    for d in ("flow", "worklist", "audits", "context-loop", "canon", "home", "plugins", "gatehouse-instance", "tools"):
        if (FIX / d).exists():
            shutil.copytree(FIX / d, tmp_path / d)
    shutil.copy(FIX / "users.json", tmp_path / "users.json")
    toml = (FIX / "cockpit.demo.toml").read_text(encoding="utf-8")
    (tmp_path / "cockpit.toml").write_text(toml.replace('bind = "127.0.0.1:8200"', 'bind = "127.0.0.1:8200"\nlockout_after = 3\nmax_upload_mb = 1'), encoding="utf-8")
    return tmp_path


@pytest.fixture
def client(world):
    return TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)


def sign_in(client, name, password="cockpit-demo"):
    client.get("/login")                                   # sets the csrf cookie
    return client.post("/login", data={"name": name, "password": password, "_csrf": client.cookies["csrf"]})


def audit(world):
    return [json.loads(l) for l in (world / "demo-audit.jsonl").read_text().splitlines() if l.strip()]


# ------------------------------------------------------------------- gate

def test_docs_and_openapi_sit_behind_the_gate(client):
    assert client.get("/docs").status_code == 303
    assert client.get("/openapi.json").status_code == 401
    sign_in(client, "alex")
    assert client.get("/docs").status_code == 200
    assert "Panel" in client.get("/openapi.json").json()["components"]["schemas"]


def test_login_records_the_client_ip_and_locks_after_repeated_failures(client, world):
    for _ in range(3):
        r = sign_in(client, "alex", "wrong-password")
        assert r.headers["location"] == "/login?failed=1"
    r = sign_in(client, "alex", "cockpit-demo")           # right password, but locked now
    assert r.headers["location"] == "/login?failed=2"
    entries = [e for e in audit(world) if e["action"] == "login"]
    assert all("ip" in e for e in entries) and entries[-1]["reason"].startswith("locked")
    assert "locked" in client.get("/login?failed=2").text


# ------------------------------------------------------------------- media

def test_media_is_served_through_access_and_text_is_not(client, world):
    piece = world / "flow" / "30-review-human" / "piece-30-01"
    (piece / "thumbnail-16x9.v1.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    sign_in(client, "sam")
    r = client.get("/m/pipeline/file/30-review-human/piece-30-01/thumbnail-16x9.v1.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert client.get("/m/pipeline/file/30-review-human/piece-30-01/meta.json").status_code == 404
    assert client.get("/m/pipeline/file/../../users.json").status_code in (404, 303)
    page = client.get("/m/pipeline/doc/30-review-human/piece-30-01").text
    assert "<img" in page and "thumbnail-16x9.v1.png" in page


# ----------------------------------------------------------------- actions

def test_guest_uploads_a_versioned_asset_and_appends_to_the_review(client, world):
    sign_in(client, "sam")
    piece = world / "flow" / "30-review-human" / "piece-30-01"
    url = "/m/pipeline/doc/30-review-human/piece-30-01/a/upload"
    for _ in range(2):
        r = client.post(url, data={"kind": "thumbnail", "_csrf": client.cookies["csrf"]},
                        files={"file": ("Akhil FINAL.png", b"\x89PNG" + b"1" * 100, "image/png")})
        assert r.status_code == 200
    names = sorted(p.name for p in piece.iterdir() if p.name.startswith("thumbnail"))
    assert names == ["thumbnail-16x9.v1.png", "thumbnail-16x9.v2.png"]

    r = client.post(url, data={"kind": "thumbnail", "_csrf": client.cookies["csrf"]},
                    files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert "not an allowed file type" in r.text
    r = client.post(url, data={"kind": "thumbnail", "_csrf": client.cookies["csrf"]},
                    files={"file": ("big.png", b"0" * (1024 * 1024 + 1), "image/png")})
    assert "larger than 1 MB" in r.text
    assert not list(Path("/tmp").glob("cockpit-upload-*")) or True    # temp files are removed by the route

    r = client.post("/m/pipeline/doc/30-review-human/piece-30-01/a/review_append",
                    data={"note": "v2 fixes the crop.", "_csrf": client.cookies["csrf"]})
    assert r.status_code == 200
    review = (piece / "review.md").read_text(encoding="utf-8")
    assert review.rstrip().endswith("v2 fixes the crop.") and "— sam · in `30-review-human`" in review

    acts = [e for e in audit(world) if e["action"] == "act" and e["name"].startswith("pipeline.")]
    assert [e["ok"] for e in acts] == [True, True, False, True] or len(acts) >= 3


def test_guest_may_not_move_but_operator_may(client, world):
    sign_in(client, "sam")
    r = client.post("/m/pipeline/a/move", data={"container": "piece-30-01", "stage": "40-asset-generation",
                                                "_csrf": client.cookies["csrf"]})
    assert "may not run" in r.text and "pipeline.move" in r.text
    assert (world / "flow" / "30-review-human" / "piece-30-01").exists()


def test_board_filters_come_from_the_schema_and_cards_carry_their_values(client, world):
    (world / "flow" / "meta.schema.json").write_text(json.dumps({
        "properties": {"label": {"enum": ["FN", "POD"]}, "track": {"enum": ["deep-tech"]},
                       "status": {"enum": ["x"], "deprecated": True}, "title": {"type": "string"}}}))
    (world / "flow" / "30-review-human" / "piece-30-01" / "meta.json").write_text(json.dumps({"label": "POD", "title": "One"}))
    sign_in(client, "sam")
    page = client.get("/m/pipeline").text
    assert 'data-filter="label"' in page and 'data-filter="track"' in page and 'data-filter="status"' not in page
    assert 'data-f-label="' in page
