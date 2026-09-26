"""Schemas are extended, never overwritten — and only in sources released for writing."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cockpit.config import ConfigError, load

TOOL = Path(__file__).resolve().parents[1] / "cockpit" / "tools" / "schema_add.py"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


@pytest.fixture
def schema(tmp_path):
    p = tmp_path / "x.schema.json"
    p.write_text(json.dumps({"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"],
                             "$defs": {"item": {"type": "object", "properties": {}}}}))
    return p


def test_an_attribute_is_added_at_top_level_and_in_a_def(schema):
    assert run(str(schema), "owner", "--type", "string", "--required").returncode == 0
    assert run(str(schema), "due", "--type", "date", "--target", "$defs.item").returncode == 0
    d = json.loads(schema.read_text())
    assert d["properties"]["owner"] == {"type": "string"} and "owner" in d["required"]
    assert d["$defs"]["item"]["properties"]["due"]["pattern"].startswith("^\\d{4}")


def test_an_existing_attribute_is_never_overwritten(schema):
    r = run(str(schema), "id", "--type", "integer")
    assert r.returncode != 0 and "never overwritten" in r.stderr
    assert json.loads(schema.read_text())["properties"]["id"] == {"type": "string"}


def test_an_enum_becomes_allowed_values(schema):
    run(str(schema), "state", "--type", "string", "--enum", "open, closed")
    assert json.loads(schema.read_text())["properties"]["state"] == {"enum": ["open", "closed"]}


def test_an_action_on_a_read_only_source_is_refused_at_load(tmp_path):
    cfg = tmp_path / "cockpit.toml"
    cfg.write_text(f'''
[[source]]
id = "data"
path = "{tmp_path}"
[[source]]
id = "tools"
path = "{tmp_path}"
[[module]]
id = "m"
plugin = "worklist"
sources = ["data"]
  [[module.action]]
  id = "x"
  tool = "tools"
  command = "t.py"
  data = "data"
  args = []
[[role]]
id = "r"
modules = ["*"]
''')
    with pytest.raises(ConfigError, match="read-write"):
        load(cfg)
