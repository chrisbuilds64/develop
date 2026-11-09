"""Spaces (ADR-027): a stage carries further live workspaces, each in a team folder of its own, apart from content."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pressroom_env.config import OpsError, load  # noqa: E402
from pressroom_env import workspace  # noqa: E402

SERVER = """
[server]
occ = "/nc/occ"
php = "php"
nextcloud_user = "nc"
groupfolders_data = "/nc/data/__groupfolders"
nextcloud_group = "team"
dav_base = "https://cloud.example.com/remote.php/dav/files/runner"
davfs_secrets = "/etc/davfs2/secrets"
runner_user = "runner"
shared = "/home/runner/shared"
envs_root = "/home/runner/envs"
claude_bin = "/home/runner/claude"
develop_repo = "https://example.com/develop.git"
users_json = "/home/runner/users.json"
cookie_secret = "/home/runner/secret"
runner_env_file = "/home/runner/runner.env"
nginx_snippet = "/etc/nginx/envs.conf"
host = "app.example.com"

[env.prod]
folder = "content"
mount = "/srv/content"
port = 8200
"""

SPACE = """
[[env.prod.space]]
id = "software"
folder = "software"
mount = "/srv/software"
application = "shipyard"
label = "Software house"
members = ["owner", "dev"]
"""


def settings(tmp_path, text):
    p = tmp_path / "envs.toml"
    p.write_text(text, encoding="utf-8")
    return load(p)


def test_a_stage_without_spaces_has_none(tmp_path):
    assert settings(tmp_path, SERVER).env("prod").spaces == ()


def test_a_space_is_read_with_its_folder_mount_and_application(tmp_path):
    sp = settings(tmp_path, SERVER + SPACE).env("prod").spaces[0]
    assert (sp.id, sp.folder, str(sp.mount), sp.application, sp.members) == ("software", "software", "/srv/software", "shipyard", ("owner", "dev"))


def test_a_space_may_not_share_a_team_folder_or_a_mount_with_a_stage(tmp_path):
    with pytest.raises(OpsError, match="team folder"):
        settings(tmp_path, SERVER + SPACE.replace('folder = "software"', 'folder = "content"'))
    with pytest.raises(OpsError, match="mount"):
        settings(tmp_path, SERVER + SPACE.replace('mount = "/srv/software"', 'mount = "/srv/content"'))


def test_a_space_without_an_application_is_refused_with_a_sentence(tmp_path):
    with pytest.raises(OpsError, match="application"):
        settings(tmp_path, SERVER + SPACE.replace('application = "shipyard"\n', ""))


def test_seeding_adds_the_application_and_the_workspace_once(tmp_path):
    st = settings(tmp_path, SERVER + SPACE)
    env = st.env("prod")
    data = {"applications": {}, "workspaces": []}
    cfg = Path("/home/runner/envs/prod/develop/apps/casefile/config")
    assert workspace._seed_spaces(data, env, cfg, st.server, {"software": 7})
    ws = data["workspaces"][0]
    assert ws["root"] == "/nc/data/__groupfolders/7/files/flow"
    assert ws["write_root"] == "/srv/software/flow"
    assert ws["mode"] == "live" and ws["members"] == ["owner", "dev"]
    assert data["applications"]["shipyard"]["config_dir"] == str(cfg / "shipyard")
    assert not workspace._seed_spaces(data, env, cfg, st.server, {"software": 7})      # idempotent
    assert len(data["workspaces"]) == 1


def test_a_space_whose_team_folder_is_not_there_yet_is_not_seeded(tmp_path):
    st = settings(tmp_path, SERVER + SPACE)
    data = {"applications": {}, "workspaces": []}
    workspace._seed_spaces(data, st.env("prod"), Path("/cfg"), st.server, {})
    assert data["workspaces"] == []
