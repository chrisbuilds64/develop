"""The desk as shelves (2026-10-20): one sentence says what waits, every piece carries the six-step path and
one button, the piece page shows the text in the page, and vocabulary.json may say the desk's words."""
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
    for name in ("flow", "home", "plugins", "tools", "users.json", "cockpit.demo.toml", "audits", "canon", "context-loop", "gatehouse-instance"):
        src = FIX / name
        if src.is_dir():
            shutil.copytree(src, tmp_path / name)
        elif src.exists():
            shutil.copy(src, tmp_path / name)
    (tmp_path / "cockpit.toml").write_text((tmp_path / "cockpit.demo.toml").read_text().replace('secret = ".demo-secret"', 'secret = ".s"'))
    return tmp_path


@pytest.fixture
def client(world):
    return TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)


def sign_in(client, name="alex", password="cockpit-demo"):
    client.get("/login")
    r = client.post("/login", data={"name": name, "password": password, "_csrf": client.cookies["csrf"]})
    assert r.status_code == 303
    client.get("/set?view=desk")


def test_the_desk_lands_on_the_home_module_and_speaks_in_one_sentence(client):
    sign_in(client)
    r = client.get("/")
    assert r.status_code == 200 and 'href="/m/pipeline"' in r.text                   # the dashboard first (2026-10-24); the desk is one click away
    assert client.get("/?all=1").status_code == 200
    desk = client.get("/m/pipeline").text
    assert "waiting for you" in desk and 'class="path ' in desk and "Waiting for you" in desk
    assert 'li class="current"' in desk and 'class="shelf shelf-you"' in desk
    assert "10-ideas" not in desk.split('class="newidea"')[0]                           # no stage folder name reaches the desk's head


def test_the_piece_page_shows_the_text_the_path_and_the_button_at_the_current_step(client, world):
    sign_in(client)
    page = client.get("/m/pipeline/doc/30-review-human/FN-041-the-long-one").text
    assert 'class="path big"' in page and page.count("<li class=") == 6
    assert "A placeholder for a longer essay." in page                                 # substack.md, rendered in the page
    assert 'class="jact"' in page and "Approve" in page.split('class="jact"')[1].split("</div>")[0]
    # a published piece says where it is instead of "nothing to do"
    out = client.get("/m/pipeline/doc/60-published/FN-ARC-01-the-first-arc").text
    assert "Nothing to do right now" not in out


def test_raw_html_in_a_draft_is_shown_not_run(client, world):
    sign_in(client)
    piece = world / "flow" / "30-review-human" / "FN-041-the-long-one"
    (piece / "substack.v2.md").write_text("# Safe\n\n<script>alert(1)</script> [x](javascript:alert(1))\n")
    page = client.get("/m/pipeline/doc/30-review-human/FN-041-the-long-one").text
    assert "<script>alert(1)</script>" not in page and "&lt;script&gt;" in page and 'href="javascript:' not in page
    assert "substack.v2.md" in page                                                    # the highest version is the one shown


def test_the_vocabulary_may_say_the_desks_words(client, world):
    vocab = json.loads((world / "flow" / "vocabulary.json").read_text())
    vocab["en"]["product"] = "Claims File"
    vocab["en"]["groups"] = {"you": "On your desk"}
    vocab["en"]["journey"] = {"idea": "Received"}
    vocab["en"]["words"] = {"desk.lead.many": "{n} cases need you.", "desk.act.read": "Read the assessment"}
    (world / "flow" / "vocabulary.json").write_text(json.dumps(vocab))
    sign_in(client)
    desk = client.get("/m/pipeline").text
    assert "Claims File" in desk and "On your desk" in desk and "cases need you." in desk and "Read the assessment" in desk
    assert 'title="Received"' in desk


def test_a_folder_without_a_record_stays_in_the_workshop(client, world):
    (world / "flow" / "30-review-human" / "nameless-folder").mkdir()
    sign_in(client)
    desk = client.get("/m/pipeline").text
    assert "nameless-folder" not in desk and "without a record" in desk
