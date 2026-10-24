"""Served under a prefix (/test): links, redirects and cookies carry it, and the stage shows in the header.

In production nginx strips the prefix and uvicorn puts it back as root_path, so the app sees the full
path and the browser's cookies are scoped to the prefix. The TestClient has no nginx in front: requests
here carry the prefix like the browser's do, and root_path tells the app where it is served — Starlette
routes on the path without the root_path either way."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from cockpit.app import create_app
from cockpit.config import ConfigError, load

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def world_with(tmp_path, extra: str):
    for d in ("flow", "worklist", "audits", "context-loop", "canon", "home", "plugins", "gatehouse-instance", "tools"):
        if (FIX / d).exists():
            shutil.copytree(FIX / d, tmp_path / d)
    shutil.copy(FIX / "users.json", tmp_path / "users.json")
    toml = (FIX / "cockpit.demo.toml").read_text(encoding="utf-8")
    (tmp_path / "cockpit.toml").write_text(toml.replace('bind = "127.0.0.1:8200"', 'bind = "127.0.0.1:8200"\n' + extra), encoding="utf-8")
    return tmp_path


@pytest.fixture
def staged(tmp_path):
    world = world_with(tmp_path, 'base_path = "/test"\nenvironment = "test"')
    return TestClient(create_app(load(world / "cockpit.toml")), root_path="/test", follow_redirects=False)


def test_the_gate_redirects_inside_the_prefix(staged):
    r = staged.get("/test/")
    assert r.status_code == 303 and r.headers["location"] == "/test/intro"


def test_links_assets_and_cookies_carry_the_prefix_and_the_stage_is_visible(staged):
    r = staged.get("/test/login")
    assert r.status_code == 200
    html = r.text
    assert '"/test/static/cockpit.css"' in html and 'action="/test/login"' in html
    assert "[TEST]" in html                       # the title says which stage this is
    assert 'href="/static/' not in html            # nothing points at the root any more
    assert all("path=/test" in c.lower() for c in r.headers.get_list("set-cookie"))


def test_sign_in_and_navigation_stay_inside_the_prefix(staged):
    staged.get("/test/login")
    r = staged.post("/test/login", data={"name": "alex", "password": "cockpit-demo", "_csrf": staged.cookies["csrf"]})
    assert r.status_code == 303 and r.headers["location"] == "/test/"
    page = staged.get("/test/")                          # the dashboard, with every link carrying the prefix
    assert page.status_code == 200
    assert 'href="/test/m/' in page.text and 'class="env env-test"' in page.text
    assert 'href="/m/' not in page.text and 'action="/m/' not in page.text   # reader links and forms carry the prefix too
    assert staged.get("/test/static/cockpit.css").status_code == 200


def test_at_the_root_nothing_changes(tmp_path):
    world = world_with(tmp_path, 'environment = "prod"')
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    r = client.get("/login")
    assert '"/static/cockpit.css"' in r.text and "[PROD]" not in r.text and "env-prod" not in r.text


def test_a_base_path_without_a_leading_slash_is_refused(tmp_path):
    world = world_with(tmp_path, 'base_path = "test"')
    with pytest.raises(ConfigError):
        load(world / "cockpit.toml")
