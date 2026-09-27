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
    u.add("alex", "cockpit-demo", "operator", "home/alex/context", "Alex")
    return u


def test_password_is_never_stored_and_wrong_ones_fail(users, tmp_path):
    raw = (tmp_path / "users.json").read_text()
    assert "cockpit-demo" not in raw
    assert users.verify("alex", "cockpit-demo") and not users.verify("alex", "Cockpit-demo") and not users.verify("nobody", "cockpit-demo")


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
    users.add("alex", "x-long-enough", "operator", "home/alex/context")
    users.add("sam", "x-long-enough", "operator", "home/sam/context")
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


# ------------------------------------------------- actions come from the plugin

def make_action_plugin(where, pid="acts", needs=("data", "tools"), actions=None):
    d = where / pid; d.mkdir(parents=True, exist_ok=True)
    (d / "reader.py").write_text("def read(access, role, module, config):\n    return {'title': 'x', 'as_of': '2026-01-01T00:00:00+00:00', 'blocks': []}\n")
    (d / "own.py").write_text("import sys\nprint('\\n'.join(sys.argv[1:]))\n")
    (d / "plugin.json").write_text(json.dumps({
        "id": pid, "name": "Acts", "version": "1.0.0", "reader": "reader.py", "needs": list(needs),
        "actions": actions if actions is not None else [
            {"id": "own", "tool": "plugin", "command": "own.py", "data": "data", "args": ["{title}"],
             "field": [{"name": "title", "required": True},
                       {"name": "kind", "type": "select", "options_from": "things.json:lov.kinds"}]},
            {"id": "ext", "tool": "tools", "command": "t.py", "data": "data", "args": []},
        ]}))
    return d


def test_a_manifest_action_that_names_a_source_outside_needs_is_refused(tmp_path):
    d = make_action_plugin(tmp_path, needs=("data",), actions=[
        {"id": "x", "tool": "plugin", "command": "own.py", "data": "elsewhere", "args": []}])
    with pytest.raises(PluginError, match="not in needs"):
        load_manifest(d)
    d = make_action_plugin(tmp_path, pid="gone", actions=[{"id": "x", "command": "missing.py", "args": []}])
    with pytest.raises(PluginError, match="not a file inside the plugin"):
        load_manifest(d)


def _world(tmp_path, module_toml, data_mode="read-write", tools=True):
    from cockpit.config import load
    make_action_plugin(tmp_path / "plugins")
    (tmp_path / "data").mkdir(exist_ok=True); (tmp_path / "tools").mkdir(exist_ok=True)
    (tmp_path / "data" / "things.json").write_text(json.dumps({"lov": {"kinds": [{"id": "a"}, {"id": "b"}]}}))
    (tmp_path / "tools" / "t.py").write_text("print('t')\n")
    (tmp_path / "cockpit.toml").write_text(f'''
[cockpit]
plugins = "plugins"
[[source]]
id = "data"
path = "{tmp_path / "data"}"
mode = "{data_mode}"
[[source]]
id = "tools"
path = "{tmp_path / "tools"}"
include = ["t.py"]
{module_toml}
[[role]]
id = "operator"
modules = ["*"]
max_sensitivity = "internal"
actions = ["*"]
''')
    return load(tmp_path / "cockpit.toml")


def test_a_module_inherits_its_plugin_actions_mapped_onto_released_sources(tmp_path):
    c = _world(tmp_path, '[[module]]\nid = "m"\nplugin = "acts"\nsources = ["data", "tools"]')
    m = c.modules[0]
    assert [a.id for a in m.actions] == ["own", "ext"] and m.withheld == ()
    assert m.actions[1].tool == "tools" and m.actions[0].data == "data"


def test_an_action_is_withheld_when_its_source_is_not_released_for_it(tmp_path):
    c = _world(tmp_path, '[[module]]\nid = "m"\nplugin = "acts"\nsources = ["data"]')
    assert [a.id for a in c.modules[0].actions] == ["own"]
    assert c.modules[0].withheld == (("ext", "needs source 'tools' (position 2 in sources)"),)
    c = _world(tmp_path, '[[module]]\nid = "m"\nplugin = "acts"\nsources = ["data", "tools"]', data_mode="read")
    assert c.modules[0].actions == () and len(c.modules[0].withheld) == 2


def test_an_instance_keeps_a_subset_and_adds_its_own_but_never_redefines(tmp_path):
    from cockpit.config import ConfigError
    c = _world(tmp_path, '[[module]]\nid = "m"\nplugin = "acts"\nsources = ["data", "tools"]\nactions = ["own"]\n'
                         '  [[module.action]]\n  id = "mine"\n  tool = "tools"\n  command = "t.py"\n  args = []')
    assert [a.id for a in c.modules[0].actions] == ["own", "mine"]
    with pytest.raises(ConfigError, match="does not redefine"):
        _world(tmp_path, '[[module]]\nid = "m"\nplugin = "acts"\nsources = ["data", "tools"]\n'
                         '  [[module.action]]\n  id = "own"\n  tool = "tools"\n  command = "t.py"\n  args = []')
    with pytest.raises(ConfigError, match="does not define"):
        _world(tmp_path, '[[module]]\nid = "m"\nplugin = "acts"\nsources = ["data", "tools"]\nactions = ["nope"]')


def test_a_value_list_can_come_from_the_data_itself(tmp_path):
    from cockpit.access import Access
    from cockpit.actions import Actions
    from cockpit.audit import AuditLog
    c = _world(tmp_path, '[[module]]\nid = "m"\nplugin = "acts"\nsources = ["data", "tools"]')
    audit = AuditLog(c.audit_path)
    acts = Actions(c, Access(c, audit), audit, {})
    m = c.modules[0]
    kind = next(f for f in m.actions[0].fields if f.name == "kind")
    assert acts.options(m.actions[0], kind, c.role("operator")) == ("a", "b")
