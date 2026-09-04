"""End-to-end walk of a pack, plus the guarantees that must not regress."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gatehouse.api import create_app
from gatehouse.config import Config, ConfigError, ModelProfile, load
from gatehouse.pack import PackError
from gatehouse.instance import Instance
from gatehouse.pack import load as load_pack

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "packs" / "example"


@pytest.fixture
def config(tmp_path: Path) -> Config:
    return Config(
        pack_path=PACK,
        instance_path=tmp_path / "instance",
        profiles={
            "none": ModelProfile(
                name="none", adapter="echo", destination="no model", local=True
            )
        },
        default_profile="none",
        task_profiles={},
        host="127.0.0.1",
        port=8100,
    )


@pytest.fixture
def client(config: Config) -> TestClient:
    return TestClient(create_app(config))


def test_full_run_produces_artifacts(client: TestClient, config: Config):
    pack = load_pack(PACK)

    assert "Start an elicitation run" in client.get("/").text

    client.post("/start", data={"client": "ChrisBuilds64"}, follow_redirects=True)

    for block in pack.blocks:
        for index, question in enumerate(block.questions):
            client.post(
                f"/block/{block.id}/answer",
                data={"question_id": question.id, "text": f"answer {index}"},
                follow_redirects=True,
            )
        client.post(f"/block/{block.id}/close", follow_redirects=True)

    interview = (config.instance_path / "interview.md").read_text()
    assert "Elicitation — ChrisBuilds64" in interview
    assert "`[AS-IS]` answer 0" in interview
    assert (config.instance_path / "run.json").exists()


def test_block_cannot_close_with_unanswered_questions(client: TestClient, config: Config):
    """Refusing must keep the operator on the block and name what is open."""
    client.post("/start", data={"client": "x"}, follow_redirects=True)
    pack = load_pack(PACK)
    block = pack.blocks[0]

    response = client.post(f"/block/{block.id}/close", follow_redirects=True)

    assert response.status_code == 200
    assert "Not finished" in response.text
    assert block.title in response.text
    assert block.questions[0].id in response.text

    run = json.loads((config.instance_path / "run.json").read_text())
    assert block.id not in run["closed_blocks"]


def test_ui_never_returns_raw_json(client: TestClient):
    """Anything reached from the navigation must render as a page."""
    for path in ("/artifacts", "/audit", "/block/outcomes", "/nonsense"):
        response = client.get(path)
        assert "text/html" in response.headers["content-type"], path
        assert not response.text.lstrip().startswith("{"), path


def test_api_path_still_returns_json(client: TestClient):
    response = client.get("/api/v1/run")
    assert response.status_code == 404
    assert response.json()["detail"] == "No run started yet."


def test_answers_survive_restart(config: Config):
    pack = load_pack(PACK)
    question = pack.blocks[0].questions[0]

    first = TestClient(create_app(config))
    first.post("/start", data={"client": "x"}, follow_redirects=True)
    first.post(
        f"/block/{pack.blocks[0].id}/answer",
        data={"question_id": question.id, "text": "their exact words"},
        follow_redirects=True,
    )

    second = TestClient(create_app(config))
    assert "their exact words" in second.get(f"/block/{pack.blocks[0].id}").text


def test_echo_adapter_logs_the_call_but_never_marks_egress(client: TestClient, config: Config):
    """The log must record every call; egress must distinguish what left."""
    pack = load_pack(PACK)
    client.post("/start", data={"client": "x"}, follow_redirects=True)
    client.post(
        f"/block/{pack.blocks[0].id}/answer",
        data={"question_id": pack.blocks[0].questions[0].id, "text": "something"},
        follow_redirects=True,
    )

    entries = [
        json.loads(line)
        for line in (config.instance_path / "audit.jsonl").read_text().splitlines()
    ]
    assert any(e["event"] == "model_call" for e in entries)
    assert not any(e.get("egress") for e in entries)


def test_missing_pack_fails_with_an_operator_message(tmp_path: Path):
    config_file = tmp_path / "gatehouse.toml"
    config_file.write_text(
        '[pack]\npath = "./nowhere"\n'
        '[instance]\npath = "./inst"\n'
        '[model]\ndefault = "a"\n'
        '[model.profiles.a]\nadapter = "echo"\ndestination = "none"\n'
    )
    with pytest.raises(ConfigError, match="not part of this repository"):
        load(config_file)


def test_pack_without_blocks_is_rejected(tmp_path: Path):
    (tmp_path / "pack.toml").write_text('[pack]\nname = "empty"\nversion = "0.1"\n')
    with pytest.raises(PackError, match="no blocks"):
        load_pack(tmp_path)


# --- Domain layers -----------------------------------------------------
#
# A layer adds and never overrides. These tests are the enforcement: if
# a layer could change core behaviour, the core would no longer be
# identical across clients and the licensing model would rest on nothing.


def _write_pack(directory: Path, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "pack.toml").write_text(body, encoding="utf-8")
    return directory


CORE = '''
[pack]
name = "core"
version = "1.0"
[[block]]
id = "one"
title = "Core block"
  [[block.question]]
  text = "Core question?"
'''


def test_layer_adds_questions_without_touching_the_core(tmp_path: Path):
    _write_pack(tmp_path / "core", CORE)
    _write_pack(tmp_path / "layer", '''
[pack]
name = "layer"
version = "0.1"
extends = "core"
[[block_extension]]
id = "one"
exit_criteria = ["something extra"]
  [[block_extension.question]]
  text = "Layer question?"
[[block]]
id = "two"
title = "Layer block"
  [[block.question]]
  text = "New block question?"
''')

    pack = load_pack(tmp_path / "layer")

    assert [b.id for b in pack.blocks] == ["one", "two"]
    assert pack.block("one").title == "Core block"
    assert [q.text for q in pack.block("one").questions] == [
        "Core question?",
        "Layer question?",
    ]
    assert pack.layers == ["core 1.0", "layer 0.1"]


def test_layer_cannot_replace_a_core_block(tmp_path: Path):
    _write_pack(tmp_path / "core", CORE)
    _write_pack(tmp_path / "layer", '''
[pack]
name = "layer"
version = "0.1"
extends = "core"
[[block]]
id = "one"
title = "Hijacked"
  [[block.question]]
  text = "Replaced?"
''')
    with pytest.raises(PackError, match="cannot replace a core block"):
        load_pack(tmp_path / "layer")


def test_layer_cannot_restate_a_core_block_title(tmp_path: Path):
    _write_pack(tmp_path / "core", CORE)
    _write_pack(tmp_path / "layer", '''
[pack]
name = "layer"
version = "0.1"
extends = "core"
[[block_extension]]
id = "one"
title = "Renamed"
''')
    with pytest.raises(PackError, match="does not restate the core"):
        load_pack(tmp_path / "layer")


def test_layer_cannot_extend_a_block_that_does_not_exist(tmp_path: Path):
    _write_pack(tmp_path / "core", CORE)
    _write_pack(tmp_path / "layer", '''
[pack]
name = "layer"
version = "0.1"
extends = "core"
[[block_extension]]
id = "nowhere"
''')
    with pytest.raises(PackError, match="not a core block"):
        load_pack(tmp_path / "layer")


def test_extension_without_extends_is_rejected(tmp_path: Path):
    _write_pack(tmp_path / "alone", '''
[pack]
name = "alone"
version = "0.1"
[[block]]
id = "one"
title = "A"
  [[block.question]]
  text = "Q?"
[[block_extension]]
id = "one"
''')
    with pytest.raises(PackError, match="no \\[pack\\] extends"):
        load_pack(tmp_path / "alone")


def test_extends_cycle_is_caught(tmp_path: Path):
    _write_pack(tmp_path / "a", '[pack]\nname = "a"\nversion = "1"\nextends = "b"\n')
    _write_pack(tmp_path / "b", '[pack]\nname = "b"\nversion = "1"\nextends = "a"\n')
    with pytest.raises(PackError, match="extends itself"):
        load_pack(tmp_path / "a")


# --- Model routing -----------------------------------------------------
#
# Not every task needs the largest model. Routing per task is what makes
# that a client decision rather than a code decision.


def _config_file(tmp_path: Path, model_section: str) -> Path:
    (tmp_path / "inst").mkdir(exist_ok=True)
    path = tmp_path / "gatehouse.toml"
    path.write_text(
        f'[pack]\npath = "{PACK}"\n'
        f'[instance]\npath = "{tmp_path / "inst"}"\n'
        f"{model_section}"
    )
    return path


def test_task_routes_to_its_own_profile(tmp_path: Path):
    config = load(_config_file(tmp_path, '''
[model]
default = "big"
[model.tasks]
followup = "small"
[model.profiles.big]
adapter = "anthropic"
model = "claude-opus-5"
destination = "Anthropic API"
[model.profiles.small]
adapter = "anthropic"
model = "claude-haiku-4-5"
destination = "Anthropic API"
'''))
    assert config.profile_for("followup").model == "claude-haiku-4-5"
    assert config.profile_for("anything-else").model == "claude-opus-5"


def test_destinations_lists_every_endpoint_reachable(tmp_path: Path):
    """What the client is told must cover every profile a task can hit."""
    config = load(_config_file(tmp_path, '''
[model]
default = "onprem"
[model.tasks]
followup = "onprem"
synthesis = "onprem"
[model.profiles.hosted]
adapter = "anthropic"
destination = "Anthropic API"
[model.profiles.onprem]
adapter = "openai_compat"
base_url = "http://localhost:11434/v1"
destination = "eigener Server"
local = true
'''))
    # `hosted` is defined but no task points at it, so it is not reachable
    # and must not appear. A destination list padded with endpoints that
    # never get called teaches the client to stop reading it.
    assert config.destinations == ["eigener Server (im Haus)"]


def test_unmapped_task_puts_the_default_destination_on_the_list(tmp_path: Path):
    """An unmapped task is not an unused task. It hits the default.

    This is the failure mode the property exists to prevent: someone maps
    the chatty task to a machine in the house, tells the client their
    answers stay there, and a second task nobody remapped ships the whole
    transcript to a hosted API. Adding `synthesis` did exactly that.
    """
    config = load(_config_file(tmp_path, '''
[model]
default = "hosted"
[model.tasks]
followup = "onprem"
[model.profiles.hosted]
adapter = "anthropic"
destination = "Anthropic API"
[model.profiles.onprem]
adapter = "openai_compat"
base_url = "http://localhost:11434/v1"
destination = "eigener Server"
local = true
'''))
    assert config.destinations == ["Anthropic API", "eigener Server (im Haus)"]


def test_unknown_task_name_is_rejected_at_startup(tmp_path: Path):
    with pytest.raises(ConfigError, match="not a task Gatehouse runs"):
        load(_config_file(tmp_path, '''
[model]
default = "a"
[model.tasks]
typo = "a"
[model.profiles.a]
adapter = "echo"
destination = "none"
'''))


def test_task_pointing_at_undefined_profile_is_rejected(tmp_path: Path):
    with pytest.raises(ConfigError, match="which is not defined"):
        load(_config_file(tmp_path, '''
[model]
default = "a"
[model.tasks]
followup = "ghost"
[model.profiles.a]
adapter = "echo"
destination = "none"
'''))


def test_profile_without_destination_is_rejected(tmp_path: Path):
    with pytest.raises(ConfigError, match="destination is required"):
        load(_config_file(tmp_path, '''
[model]
default = "a"
[model.profiles.a]
adapter = "echo"
'''))


def test_missing_credentials_surface_as_an_operator_message(monkeypatch, tmp_path: Path):
    """A machine with no sign-in must not produce a stack trace.

    The SDK raises a bare TypeError when it can resolve no credentials.
    That is the most likely failure on a fresh client machine, and the
    operator is usually not alone in the room when it happens.
    """
    from gatehouse.adapters import ModelError, build
    from gatehouse.audit import AuditLog

    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://127.0.0.1:1")

    profile = ModelProfile(
        name="hosted", adapter="anthropic", model="claude-opus-5",
        destination="Anthropic API",
    )
    with pytest.raises(ModelError) as exc:
        build(profile, AuditLog(tmp_path)).ask("check", "ping")
    assert "Keine Anmeldung gefunden" in str(exc.value) or "fehlgeschlagen" in str(exc.value)


def test_named_key_variable_that_is_unset_is_reported(tmp_path: Path, monkeypatch):
    from gatehouse.adapters import ModelError, build
    from gatehouse.audit import AuditLog

    monkeypatch.delenv("CLIENT_KEY", raising=False)
    profile = ModelProfile(
        name="client", adapter="anthropic", destination="Anthropic API",
        api_key_env="CLIENT_KEY",
    )
    with pytest.raises(ModelError, match="CLIENT_KEY"):
        build(profile, AuditLog(tmp_path))


# ---------------------------------------------------------------------
# Reading the answers back
# ---------------------------------------------------------------------


def _pack_with_synthesis(tmp_path: Path, synthesis: str = "") -> Path:
    directory = tmp_path / "pack"
    directory.mkdir()
    (directory / "pack.toml").write_text('''
[pack]
name = "Short"
version = "0.1"
[[block]]
id = "a"
title = "A"
[[block.question]]
id = "a.1"
text = "What do you build?"
''' + synthesis, encoding="utf-8")
    return directory


def test_pack_without_synthesis_offers_no_reading(tmp_path: Path):
    """Absence is a valid state, not a broken pack."""
    pack = load_pack(_pack_with_synthesis(tmp_path))
    assert pack.synthesis is None


def test_synthesis_without_a_prompt_is_rejected(tmp_path: Path):
    """A reading with no instruction is the model's agenda, not the pack's."""
    with pytest.raises(PackError, match="defines no prompt"):
        load_pack(_pack_with_synthesis(tmp_path, '''
[synthesis]
title = "What your answers say"
'''))


def test_synthesis_is_read_from_the_pack(tmp_path: Path):
    pack = load_pack(_pack_with_synthesis(tmp_path, '''
[synthesis]
title = "What your answers say"
lead = "This is a reading of your answers."
prompt = "Report contradictions only."
'''))
    assert pack.synthesis.title == "What your answers say"
    assert pack.synthesis.prompt == "Report contradictions only."


def test_reading_sends_only_answered_questions(tmp_path: Path):
    """Blanks invite the model to treat silence as a finding."""
    from gatehouse import synthesize

    pack = load_pack(_pack_with_synthesis(tmp_path, '''
[[block]]
id = "b"
title = "B"
[[block.question]]
id = "b.1"
text = "Who signs it off?"

[synthesis]
prompt = "Report contradictions only."
'''))
    instance = Instance(tmp_path / "instance", pack)
    run = instance.start("Acme")
    instance.record(run, "a.1", "We build gearboxes.", "AS-IS")

    sent: list[str] = []
    models = _recording_registry(sent, reply="### A finding\n> \"x\" (a.1)\nSomething.")
    synthesize.read_back(models, pack, run)

    assert "We build gearboxes." in sent[0]
    assert "Who signs it off?" not in sent[0]


def test_reading_refuses_an_empty_run(tmp_path: Path):
    from gatehouse import synthesize

    pack = load_pack(_pack_with_synthesis(tmp_path, '''
[synthesis]
prompt = "Report contradictions only."
'''))
    instance = Instance(tmp_path / "instance", pack)
    run = instance.start("Acme")

    with pytest.raises(synthesize.SynthesisUnavailable, match="nothing to read back"):
        synthesize.read_back(_recording_registry([], reply=""), pack, run)


def test_a_failed_reading_does_not_cost_the_interview(tmp_path: Path):
    """The answers are on disk. A model outage costs the reading only."""
    from gatehouse import synthesize
    from gatehouse.adapters import ModelError

    pack = load_pack(_pack_with_synthesis(tmp_path, '''
[synthesis]
prompt = "Report contradictions only."
'''))
    instance = Instance(tmp_path / "instance", pack)
    run = instance.start("Acme")
    instance.record(run, "a.1", "We build gearboxes.", "AS-IS")

    class Failing:
        def for_task(self, task):
            raise ModelError("no credentials")

    with pytest.raises(synthesize.SynthesisUnavailable, match="no credentials"):
        synthesize.read_back(Failing(), pack, run)

    assert "We build gearboxes." in instance.interview_file.read_text(encoding="utf-8")


def test_the_reading_is_its_own_artifact(tmp_path: Path):
    """Derived from run.json, never written into it."""
    pack = load_pack(_pack_with_synthesis(tmp_path, '''
[synthesis]
title = "What your answers say"
lead = "A reading of your answers."
prompt = "Report contradictions only."
'''))
    instance = Instance(tmp_path / "instance", pack)
    run = instance.start("Acme")
    instance.record(run, "a.1", "We build gearboxes.", "AS-IS")

    text = instance.save_analysis(run, "What your answers say", "A reading.", "### Finding")

    assert instance.analysis_file.exists()
    assert "What your answers say" in text
    assert "Finding" in instance.analysis_file.read_text(encoding="utf-8")
    assert "Finding" not in instance.state_file.read_text(encoding="utf-8")


def _recording_registry(sent: list[str], reply: str):
    class Recorder:
        def ask(self, task, prompt, context=None):
            sent.append(prompt)
            return reply

    class Registry:
        def for_task(self, task):
            return Recorder()

    return Registry()


def test_an_empty_reply_is_not_an_empty_finding_list(tmp_path: Path):
    """The echo adapter returns nothing. That must read as no reading.

    An empty string reaching the page looks identical to a reading that
    found nothing worth reporting, which is the strongest possible claim
    this form can make and the one it least deserves to make by accident.
    """
    from gatehouse import synthesize

    pack = load_pack(_pack_with_synthesis(tmp_path, '''
[synthesis]
prompt = "Report contradictions only."
'''))
    instance = Instance(tmp_path / "instance", pack)
    run = instance.start("Acme")
    instance.record(run, "a.1", "We build gearboxes.", "AS-IS")

    with pytest.raises(synthesize.SynthesisUnavailable, match="nichts zurückgegeben"):
        synthesize.read_back(_recording_registry([], reply="   "), pack, run)
