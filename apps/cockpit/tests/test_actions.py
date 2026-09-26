"""Actions run the tool that owns the data — never a shell, never without a grant."""

import pytest

from cockpit.access import Access, Denied
from cockpit.actions import Actions
from cockpit.audit import AuditLog
from cockpit.config import load


@pytest.fixture
def world(tmp_path):
    tools = tmp_path / "tools"; tools.mkdir()
    # A stand-in tool: prints its arguments, one per line, so the test can see the argv.
    (tools / "echo.py").write_text("import sys\nprint('\\n'.join(sys.argv[1:]))\n", encoding="utf-8")
    (tools / "secret.py").write_text("print('should never run')\n", encoding="utf-8")
    cfg = tmp_path / "cockpit.toml"
    cfg.write_text(f"""
[cockpit]
audit = "audit.jsonl"
default_role = "operator"

[[source]]
id = "tools"
path = "{tools}"
include = ["echo.py"]
sensitivity = "internal"

[[module]]
id = "m"
reader = "x"
sources = []
maturity = "running"
  [[module.action]]
  id = "say"
  tool = "tools"
  command = "echo.py"
  args = ["add", "{{title}}", "--due", "{{due}}", "--flag"]
    [[module.action.field]]
    name = "title"
    required = true
    [[module.action.field]]
    name = "due"
    type = "date"
  [[module.action]]
  id = "hidden"
  tool = "tools"
  command = "secret.py"
  args = []

[[role]]
id = "operator"
modules = ["*"]
max_sensitivity = "internal"
actions = ["m.say"]

[[role]]
id = "guest"
modules = ["*"]
max_sensitivity = "internal"
""", encoding="utf-8")
    config = load(cfg)
    audit = AuditLog(config.audit_path)
    access = Access(config, audit)
    return config, Actions(config, access, audit), audit


def test_values_become_arguments_never_a_shell(world):
    config, actions, _ = world
    m = config.modules[0]
    out = actions.run(m, actions.find(m, "say"), {"title": "a; rm -rf / && echo pwned", "due": "2026-10-01"},
                      config.role("operator"))
    assert out.ok
    # The whole injection attempt arrives as ONE argument, untouched, harmless.
    assert out.output.splitlines() == ["add", "a; rm -rf / && echo pwned", "--due", "2026-10-01", "--flag"]


def test_an_empty_optional_field_drops_its_flag(world):
    config, actions, _ = world
    m = config.modules[0]
    out = actions.run(m, actions.find(m, "say"), {"title": "x", "due": ""}, config.role("operator"))
    assert out.output.splitlines() == ["add", "x", "--flag"]


def test_a_required_field_cannot_be_empty(world):
    config, actions, _ = world
    m = config.modules[0]
    with pytest.raises(Denied, match="required"):
        actions.run(m, actions.find(m, "say"), {"title": ""}, config.role("operator"))


def test_a_role_without_the_grant_is_refused_and_logged(world):
    config, actions, audit = world
    m = config.modules[0]
    with pytest.raises(Denied, match="may not run"):
        actions.run(m, actions.find(m, "say"), {"title": "x"}, config.role("guest"))
    last = list(audit.entries())[-1]
    assert last["action"] == "act" and last["ok"] is False and "may not run" in last["reason"]


def test_a_script_not_released_from_its_source_does_not_run(world):
    config, actions, _ = world
    m = config.modules[0]
    role = config.role("operator")
    # operator has no grant for m.hidden; give one and it must still fail on release
    from dataclasses import replace
    role = replace(role, actions=("*",))
    with pytest.raises(Denied, match="not released"):
        actions.run(m, actions.find(m, "hidden"), {}, role)
