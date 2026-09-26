"""Users: hashes, signed sessions, per-user sources. Plugins: manifests, install, shadowing."""

import json
import time

import pytest

from cockpit.access import Access
from cockpit.audit import AuditLog
from cockpit.config import load
from cockpit.plugins import PluginError, add, discover, load_manifest, remove
from cockpit.users import Users


# ------------------------------------------------------------------- users

@pytest.fixture
def users(tmp_path):
    u = Users(tmp_path / "users.json", tmp_path / ".secret")
    u.add("alex", "demo", "operator", "home/alex/context", "Alex")
    return u


def test_password_is_never_stored_and_wrong_ones_fail(users, tmp_path):
    raw = (tmp_path / "users.json").read_text()
    assert "demo" not in raw
    assert users.verify("alex", "demo") and not users.verify("alex", "Demo") and not users.verify("nobody", "demo")


def test_a_session_token_is_signed_and_tampering_is_detected(users):
    tok = users.issue("alex")
    assert users.redeem(tok) == "alex"
    name, exp, sig = tok.split("|")
    assert users.redeem(f"sam|{exp}|{sig}") is None          # different name, same signature
    assert users.redeem(f"{name}|{int(time.time()) - 10}|{sig}") is None   # expired, and signature no longer fits
    assert users.redeem("garbage") is None and users.redeem(None) is None


def test_the_secret_file_is_private(users, tmp_path):
    users.issue("alex")
    assert oct((tmp_path / ".secret").stat().st_mode & 0o777) == "0o600"


def test_a_source_with_user_context_resolves_per_user(tmp_path):
    (tmp_path / "home/alex/context").mkdir(parents=True)
    (tmp_path / "home/alex/context/todo.json").write_text('{"who": "alex"}')
    (tmp_path / "home/sam/context").mkdir(parents=True)
    (tmp_path / "home/sam/context/todo.json").write_text('{"who": "sam"}')
    cfg = tmp_path / "cockpit.toml"
    cfg.write_text('''
[cockpit]
default_role = "operator"
[[source]]
id = "context"
path = "{user.context}"
sensitivity = "internal"
[[role]]
id = "operator"
modules = ["*"]
max_sensitivity = "internal"
''')
    config = load(cfg)
    users = Users(config.users_path, config.secret_path)
    users.add("alex", "x", "operator", "home/alex/context")
    users.add("sam", "x", "operator", "home/sam/context")
    audit = AuditLog(config.audit_path)
    for name in ("alex", "sam"):
        u = users.get(name, config.base_dir)
        access = Access(config, audit, u.as_vars())
        assert access.read_json("context", "todo.json", config.role()) == {"who": name}


# ----------------------------------------------------------------- plugins

def make_plugin(where, pid="hello", extra=None):
    d = where / pid
    d.mkdir(parents=True)
    (d / "plugin.json").write_text(json.dumps({"id": pid, "name": "Hello", "version": "1.0.0",
                                               "reader": "reader.py", **(extra or {})}))
    (d / "reader.py").write_text("def read(access, role, module, config):\n    return {'hello': True}\n")
    return d


def test_a_manifest_with_an_unknown_field_is_refused(tmp_path):
    d = make_plugin(tmp_path, extra={"surprise": 1})
    with pytest.raises(PluginError, match="unknown field"):
        load_manifest(d)


def test_install_copies_and_list_finds_it(tmp_path):
    src = make_plugin(tmp_path / "src")
    installed = tmp_path / "plugins"
    p = add(src, installed)
    assert p.path == (installed / "hello").resolve() and not p.bundled
    found = discover(installed)
    assert "hello" in found and found["hello"].version == "1.0.0"
    assert remove("hello", installed) and "hello" not in discover(installed)


def test_link_installs_a_symlink(tmp_path):
    src = make_plugin(tmp_path / "src")
    installed = tmp_path / "plugins"
    add(src, installed, link=True)
    assert (installed / "hello").is_symlink()


def test_an_installed_plugin_shadows_a_bundled_one(tmp_path):
    installed = tmp_path / "plugins"
    make_plugin(installed, pid="worklist", extra={"version": "9.9.9"})
    found = discover(installed)
    assert found["worklist"].version == "9.9.9" and not found["worklist"].bundled
