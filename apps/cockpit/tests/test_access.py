"""The guarantees that must not regress.

Each test name states the guarantee. They run against a temporary directory
tree, so a failure here is a failure of the code, never of the environment.
"""

import json
import os

import pytest

from cockpit.access import Access, Denied
from cockpit.audit import AuditLog
from cockpit.config import ConfigError, load


def write_config(tmp_path, body):
    p = tmp_path / "cockpit.toml"
    p.write_text(body, encoding="utf-8")
    return p


@pytest.fixture
def world(tmp_path):
    """A released source with two files, one of them withheld; a secret outside."""
    src = tmp_path / "data"
    src.mkdir()
    (src / "todo.json").write_text('{"ok": true}', encoding="utf-8")
    (src / "private.json").write_text('{"secret": 1}', encoding="utf-8")
    (tmp_path / "outside.txt").write_text("not yours", encoding="utf-8")
    os.symlink(tmp_path / "outside.txt", src / "link.txt")

    cfg = write_config(tmp_path, f"""
[cockpit]
name = "Test"
audit = "audit.jsonl"
default_role = "operator"

[[source]]
id = "data"
label = "Data"
path = "{src}"
include = ["todo.json", "link.txt"]
sensitivity = "internal"

[[source]]
id = "open"
label = "Open dir"
path = "{src}"
sensitivity = "confidential"

[[module]]
id = "worklist"
reader = "cockpit.readers.worklist"
sources = ["data"]
maturity = "running"

[[role]]
id = "operator"
modules = ["*"]
max_sensitivity = "internal"

[[role]]
id = "guest"
modules = ["worklist"]
max_sensitivity = "public"
""")
    config = load(cfg)
    audit = AuditLog(config.audit_path)
    return config, Access(config, audit), audit


# ------------------------------------------------------------- containment

def test_a_released_file_is_readable(world):
    config, access, _ = world
    assert access.read_json("data", "todo.json", config.role()) == {"ok": True}


def test_dotdot_cannot_leave_the_source(world):
    config, access, _ = world
    with pytest.raises(Denied):
        access.resolve("open", "../outside.txt", config.role())


def test_a_symlink_cannot_leave_the_source_even_when_released(world):
    config, access, _ = world
    with pytest.raises(Denied, match="escapes"):
        access.resolve("data", "link.txt", config.role())


def test_absolute_paths_are_refused(world):
    config, access, _ = world
    with pytest.raises(Denied):
        access.resolve("open", str(config.sources["open"].path / "todo.json"), config.role())


# ------------------------------------------------------------ release list

def test_a_file_not_on_the_release_list_is_refused(world):
    config, access, _ = world
    with pytest.raises(Denied, match="not released"):
        access.resolve("data", "private.json", config.role())


def test_listing_hides_what_the_release_withholds(world):
    config, access, _ = world
    assert access.listdir("data", config.role()) == ["link.txt", "todo.json"]


# ------------------------------------------------------------------ roles

def test_a_role_cannot_read_above_its_ceiling(world):
    config, access, _ = world
    with pytest.raises(Denied, match="may not read"):
        access.resolve("open", "todo.json", config.role("operator"))   # confidential > internal


def test_guest_cannot_read_internal(world):
    config, access, _ = world
    with pytest.raises(Denied):
        access.resolve("data", "todo.json", config.role("guest"))


def test_role_module_grant(world):
    config, _, _ = world
    assert config.role("guest").may_open("worklist")
    assert not config.role("guest").may_open("gatehouse")
    assert config.role("operator").may_open("anything")


# ------------------------------------------------------------------ audit

def test_every_attempt_is_recorded_refused_ones_with_a_reason(world):
    config, access, audit = world
    access.read_json("data", "todo.json", config.role())
    with pytest.raises(Denied):
        access.resolve("data", "private.json", config.role())
    entries = list(audit.entries())
    assert [e["ok"] for e in entries] == [True, False]
    assert "reason" in entries[1]
    assert all("ts" in e and "role" in e for e in entries)


def test_refusal_happens_before_the_disk_is_touched(world, monkeypatch):
    """A refused request must not resolve the path — no disk access on deny."""
    config, access, _ = world
    from pathlib import Path
    called = []
    real = Path.resolve
    monkeypatch.setattr(Path, "resolve", lambda self, strict=False: called.append(self) or real(self, strict=strict))
    with pytest.raises(Denied):
        access.resolve("data", "private.json", config.role())
    assert called == []


# --------------------------------------------------------- configuration

def test_a_module_needing_an_undefined_source_fails_at_load(tmp_path):
    cfg = write_config(tmp_path, """
[[module]]
id = "x"
reader = "r"
sources = ["nope"]
maturity = "running"
[[role]]
id = "r"
modules = ["*"]
""")
    with pytest.raises(ConfigError, match="not defined"):
        load(cfg)


def test_no_roles_means_no_start(tmp_path):
    cfg = write_config(tmp_path, "[cockpit]\nname='x'\n")
    with pytest.raises(ConfigError, match="role"):
        load(cfg)


def test_unknown_sensitivity_is_refused(tmp_path):
    cfg = write_config(tmp_path, f"""
[[source]]
id = "s"
path = "{tmp_path}"
sensitivity = "secret"
[[role]]
id = "r"
modules = ["*"]
""")
    with pytest.raises(ConfigError, match="not allowed"):
        load(cfg)


def test_default_role_must_exist(tmp_path):
    cfg = write_config(tmp_path, """
[cockpit]
default_role = "ghost"
[[role]]
id = "r"
modules = ["*"]
""")
    with pytest.raises(ConfigError, match="default_role"):
        load(cfg)


def test_short_cache_serves_back_navigation_and_forgets_after_an_action(tmp_path):
    from cockpit.access import Access
    from cockpit.audit import AuditLog
    from cockpit.config import load
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.json").write_text('{"n": 1}')
    (tmp_path / "cockpit.toml").write_text('''
[cockpit]
default_role = "operator"
cache_seconds = 60
[[source]]
id = "data"
path = "data"
sensitivity = "internal"
[[role]]
id = "operator"
modules = ["*"]
max_sensitivity = "internal"
''')
    cfg = load(tmp_path / "cockpit.toml")
    Access.forget()
    acc = Access(cfg, AuditLog(tmp_path / "audit.jsonl"), {})
    role = cfg.role()
    assert acc.read_json("data", "x.json", role) == {"n": 1}
    (tmp_path / "data" / "x.json").write_text('{"n": 2}')
    assert acc.read_json("data", "x.json", role) == {"n": 1}          # within the ttl: the kept value
    assert "x.json" in acc.listdir("data", role)
    Access.forget()
    assert acc.read_json("data", "x.json", role) == {"n": 2}          # after an action: fresh
    audit = (tmp_path / "audit.jsonl").read_text()
    assert audit.count('"action": "read"') == 3                        # every call is still recorded
