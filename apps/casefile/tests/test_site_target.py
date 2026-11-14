"""A static site as a deploy target (REQ-008): the plan is the gate, nothing is deleted, protected paths are never
written, what is replaced is kept, and what is served is compared with the source."""

import json

import pytest

from casefile.connectors import site as s


def _site(tmp_path, **extra):
    src = tmp_path / "website"
    (src / "art").mkdir(parents=True)
    (src / "drafts").mkdir()
    (src / "_data").mkdir()
    (src / "index.html").write_text("<h1>new</h1>")
    (src / "about.html").write_text("about")
    (src / "art" / "a.jpg").write_bytes(b"\xff\xd8image")
    (src / "README.md").write_text("not for the server")
    (src / "drafts" / "script.md").write_text("not for the server either")
    (src / "_data" / "index.html").write_text("an empty shell")
    (src / ".DS_Store").write_bytes(b"x")
    live = tmp_path / "live"
    (live / "_data").mkdir(parents=True)
    (live / "index.html").write_text("<h1>old</h1>")
    (live / "about.html").write_text("about")
    (live / "old-page.html").write_text("only the server has this")
    (live / "secrets.php").write_text("<?php $key = 'k';")
    (live / "_data" / "list.csv").write_text("a@example.org")
    desc = {
        "source": "website",
        "target": {"kind": "dir", "path": "live"},
        "url": "https://example.org",
        "exclude": ["README.md", "drafts/**"],
        "protected": ["secrets.php", "_data/**"],
        "must_not_serve": ["_data/list.csv"],
        **extra,
    }
    path = tmp_path / "site.json"
    path.write_text(json.dumps(desc))
    site = s.Site.load(path)
    return site, s.open_target(site, tmp_path), live, src


def test_the_plan_sorts_every_file_and_touches_nothing(tmp_path):
    site, target, live, _ = _site(tmp_path)
    before = target.listing()
    plan = s.make_plan(site, target)
    assert plan.new == ["art/a.jpg"]
    assert plan.changed == ["index.html"]
    assert plan.same == ["about.html"]
    assert plan.server_only == ["old-page.html"]
    assert plan.protected == ["_data/list.csv", "secrets.php"]
    assert plan.held_back == ["_data/index.html"]
    assert target.listing() == before and (live / "index.html").read_text() == "<h1>old</h1>"


def test_excluded_and_protected_files_never_leave_the_source(tmp_path):
    site, _, _, _ = _site(tmp_path)
    assert sorted(s.local_files(site)) == ["about.html", "art/a.jpg", "index.html"]


def test_apply_uploads_the_approved_plan_and_keeps_what_it_replaces(tmp_path):
    site, target, live, _ = _site(tmp_path)
    plan = s.make_plan(site, target)
    done = s.apply_plan(site, target, plan.id, tmp_path / "kept")
    assert done.uploaded == ["art/a.jpg", "index.html"]
    assert (live / "index.html").read_text() == "<h1>new</h1>"
    assert (live / "art" / "a.jpg").read_bytes() == b"\xff\xd8image"
    assert (tmp_path / "kept" / f"replaced-{plan.id}" / "index.html").read_text() == "<h1>old</h1>"
    # nothing deleted, nothing protected written, nothing excluded uploaded
    assert (live / "old-page.html").exists()
    assert (live / "secrets.php").read_text() == "<?php $key = 'k';"
    assert (live / "_data" / "list.csv").read_text() == "a@example.org"
    assert not (live / "_data" / "index.html").exists()
    assert not (live / "README.md").exists() and not (live / "drafts").exists()
    assert not list(live.rglob("*.tmp-upload"))
    assert s.make_plan(site, target).uploads == []


def test_apply_refuses_when_the_source_changed_after_the_plan_was_read(tmp_path):
    site, target, live, src = _site(tmp_path)
    plan = s.make_plan(site, target)
    (src / "index.html").write_text("<h1>changed after approval</h1>")
    with pytest.raises(s.SiteError, match="Nothing was uploaded"):
        s.apply_plan(site, target, plan.id, tmp_path / "kept")
    assert (live / "index.html").read_text() == "<h1>old</h1>" and not (live / "art").exists()


def test_apply_refuses_when_the_server_changed_after_the_plan_was_read(tmp_path):
    site, target, live, _ = _site(tmp_path)
    plan = s.make_plan(site, target)
    (live / "index.html").write_text("<h1>somebody edited the server by hand</h1>")
    with pytest.raises(s.SiteError):
        s.apply_plan(site, target, plan.id, tmp_path / "kept")


def _serving(live, extra=None):
    def fetch(url):
        path = url.removeprefix("https://example.org/")
        if extra and path in extra:
            return extra[path]
        f = live / path
        return (200, f.read_bytes()) if f.is_file() else (404, b"")

    return fetch


def test_verify_compares_what_is_served_with_the_source(tmp_path):
    site, target, live, _ = _site(tmp_path)
    blocked = {"_data/list.csv": (403, b"")}
    before = s.verify(site, _serving(live, blocked))
    assert not before.ok and before.differs == ["index.html"] and before.missing == ["art/a.jpg (404)"]
    s.apply_plan(site, target, s.make_plan(site, target).id, tmp_path / "kept")
    after = s.verify(site, _serving(live, blocked))
    assert after.ok and after.served == 3


def test_verify_fails_when_a_file_that_must_stay_private_is_served(tmp_path):
    site, target, live, _ = _site(tmp_path)
    s.apply_plan(site, target, s.make_plan(site, target).id, tmp_path / "kept")
    v = s.verify(site, _serving(live))  # the stand-in server hands out the list
    assert not v.ok and v.exposed == ["_data/list.csv"]


def test_a_description_with_an_unknown_key_or_without_a_source_is_refused(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps({"source": "nowhere", "target": {"kind": "dir", "path": "x"}}))
    with pytest.raises(s.SiteError, match="does not exist"):
        s.Site.load(tmp_path / "a.json")
    (tmp_path / "website").mkdir()
    (tmp_path / "b.json").write_text(json.dumps({"source": "website", "target": {}, "delete": True}))
    with pytest.raises(s.SiteError, match="unknown keys"):
        s.Site.load(tmp_path / "b.json")


def test_credentials_come_from_the_environment_or_a_named_file_never_from_the_description(tmp_path, monkeypatch):
    monkeypatch.delenv("SITE_USER", raising=False)
    monkeypatch.delenv("SITE_PASSWORD", raising=False)
    with pytest.raises(s.SiteError, match="no credentials"):
        s.credentials({"kind": "ftps", "host": "ftp.example.org"}, tmp_path)
    (tmp_path / "secret").write_text("user1\npass1\n")
    assert s.credentials({"secret": "secret"}, tmp_path) == ("user1", "pass1")
    monkeypatch.setenv("SITE_USER", "u")
    monkeypatch.setenv("SITE_PASSWORD", "p")
    assert s.credentials({"secret": "secret"}, tmp_path) == ("u", "p")


def test_the_command_line_plans_applies_and_writes_a_report(tmp_path, capsys):
    _site(tmp_path)
    desc = str(tmp_path / "site.json")
    assert s.main(["plan", desc, "--report", str(tmp_path / "plan.json")]) == 0
    plan = json.loads((tmp_path / "plan.json").read_text())
    assert plan["step"] == "plan" and plan["changed"] == ["index.html"]
    assert s.main(["apply", desc]) == 2  # no approved plan named
    assert s.main(["apply", desc, "--plan", "000000000000"]) == 2
    assert s.main(["apply", desc, "--plan", plan["id"], "--keep", str(tmp_path / "kept")]) == 0
    assert (tmp_path / "live" / "index.html").read_text() == "<h1>new</h1>"
    assert "uploaded: 2 files" in capsys.readouterr().out


def test_publish_asks_once_and_a_no_uploads_nothing(tmp_path):
    _, _, live, _ = _site(tmp_path)
    desc = str(tmp_path / "site.json")
    asked = []
    assert s.main(["publish", desc, "--report", str(tmp_path / "r.json")], confirm=lambda p: asked.append(p.id) or False) == 0
    assert len(asked) == 1 and (live / "index.html").read_text() == "<h1>old</h1>"
    assert json.loads((tmp_path / "r.json").read_text())["approved"] is False


def test_publish_with_a_yes_uploads_the_plan_shown_and_verifies_it(tmp_path):
    _, _, live, _ = _site(tmp_path)
    desc = str(tmp_path / "site.json")
    fetch = _serving(live, {"_data/list.csv": (403, b"")})
    code = s.main(["publish", desc, "--keep", str(tmp_path / "kept"), "--report", str(tmp_path / "r.json")], confirm=lambda p: True, fetch=fetch)
    report = json.loads((tmp_path / "r.json").read_text())
    assert code == 0 and report["verified"]["ok"] and report["applied"]["plan"] == report["plan"]["id"]
    assert (live / "index.html").read_text() == "<h1>new</h1>"
    # a second run finds nothing to upload, asks nothing, and still verifies
    assert s.main(["publish", desc], confirm=lambda p: pytest.fail("asked without anything to upload"), fetch=fetch) == 0
