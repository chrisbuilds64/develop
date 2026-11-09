"""Deploy requests (ADR-028): a helper asks, the server checks the gate on the case itself, deploys only a tag on main,
and reports back to the case. A space never deploys above its own stage."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pressroom_env import requests  # noqa: E402
from pressroom_env.config import OpsError, load  # noqa: E402

CFG = Path(__file__).resolve().parents[3] / "apps" / "casefile" / "config" / "shipyard"
CASE = "SW-2026-001-split-the-api"


def world(tmp_path: Path, monkeypatch, on_main=True):
    envs = tmp_path / "envs"
    text = f"""
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
envs_root = "{envs}"
claude_bin = "/home/runner/claude"
develop_repo = "https://example.com/develop.git"
users_json = "/home/runner/users.json"
cookie_secret = "/home/runner/secret"
runner_env_file = "/home/runner/runner.env"
nginx_snippet = "/etc/nginx/envs.conf"
host = "app.example.com"

[env.prod]
folder = "content"
mount = "{tmp_path}/srv/content"
port = 8200

[env.test]
folder = "content-test"
mount = "{tmp_path}/srv/content-test"
port = 8201
base_path = "/test"
clone_from = "prod"

[env.entw]
folder = "content-entw"
mount = "{tmp_path}/srv/content-entw"
port = 8202
base_path = "/entw"
clone_from = "prod"

[[env.prod.space]]
id = "shipyard"
folder = "shipyard"
mount = "{tmp_path}/srv/shipyard"
application = "shipyard"
label = "Shipyard"

[[env.entw.space]]
id = "shipyard"
folder = "shipyard-entw"
mount = "{tmp_path}/srv/shipyard-entw"
application = "shipyard"
label = "Shipyard"
"""
    (tmp_path / "envs.toml").write_text(text, encoding="utf-8")
    st = load(tmp_path / "envs.toml")
    for name in ("prod", "entw"):
        shutil.copytree(CFG, st.env(name).dir(st.server) / "develop" / "apps" / "casefile" / "config" / "shipyard")
    for space in ("shipyard", "shipyard-entw"):
        for s in json.loads((CFG / "stages.json").read_text(encoding="utf-8"))["stages"]:
            (tmp_path / "srv" / space / "flow" / s["folder"]).mkdir(parents=True)

    def fake_on_main(settings, env, tag):
        if not on_main:
            raise OpsError(f"{tag} (abc) is not on main")
        return "abc123"

    def fake_run(cmd, user=None, input=None, **kw):                 # the runner's write, without sudo
        path = Path(cmd[-1])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(input, encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(requests, "on_main", fake_on_main)
    monkeypatch.setattr(requests, "run", fake_run)
    return st


def case_in(tmp_path, stage, space="shipyard"):
    d = tmp_path / "srv" / space / "flow" / stage / CASE
    d.mkdir()
    return d


def ask(tmp_path, **req):
    spool = tmp_path / "spool"
    spool.mkdir(exist_ok=True)
    body = {"stage": "entw", "tag": "v2026.11.1", "space_stage": "prod", "space": "shipyard", "case": CASE, **req}
    (spool / "r1.json").write_text(json.dumps(body), encoding="utf-8")
    return spool


deployed: list = []


def deploy(stage, tag, config=None):
    deployed.append((stage, tag))
    return subprocess.CompletedProcess([], 0, "prod: abc123 deployed and restarted\n", "")


def verify_orders(tmp_path, space="shipyard"):
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted((tmp_path / "srv" / space / "flow" / "_runs").glob("*.json"))]


def test_an_accepted_release_is_deployed_and_reported_to_the_case(tmp_path, monkeypatch):
    st = world(tmp_path, monkeypatch)
    case_in(tmp_path, "50-release")
    deployed.clear()
    [r] = requests.serve(st, ask(tmp_path), deploy=deploy)
    assert r["outcome"] == "deployed" and deployed == [("entw", "v2026.11.1")]
    [order] = verify_orders(tmp_path)
    assert order["skill"] == "shipyard-verify" and order["container"] == f"50-release/{CASE}" and '"deployed"' in order["note"]
    assert not list((tmp_path / "spool").glob("*.json")) and (tmp_path / "spool" / "done" / "r1.result.json").is_file()


def test_a_stage_the_case_has_not_been_released_to_is_refused_and_the_case_hears_why(tmp_path, monkeypatch):
    st = world(tmp_path, monkeypatch)
    case_in(tmp_path, "60-entw")                                         # ENTW not yet accepted
    deployed.clear()
    [r] = requests.serve(st, ask(tmp_path, stage="test"), deploy=deploy)
    assert r["outcome"] == "refused" and "not in 70-test" in r["reason"] and deployed == []
    [order] = verify_orders(tmp_path)
    assert order["container"] == f"60-entw/{CASE}" and "refused" in order["note"]


def test_a_trial_on_entw_never_reaches_production(tmp_path, monkeypatch):
    st = world(tmp_path, monkeypatch)
    case_in(tmp_path, "80-prod", space="shipyard-entw")
    deployed.clear()
    [r] = requests.serve(st, ask(tmp_path, stage="prod", space_stage="entw"), deploy=deploy)
    assert r["outcome"] == "refused" and "may not deploy to prod" in r["reason"] and deployed == []


def test_only_a_tag_on_main_is_deployed(tmp_path, monkeypatch):
    st = world(tmp_path, monkeypatch, on_main=False)
    case_in(tmp_path, "50-release")
    deployed.clear()
    [r] = requests.serve(st, ask(tmp_path), deploy=deploy)
    assert r["outcome"] == "refused" and "not on main" in r["reason"] and deployed == []


@pytest.mark.parametrize("tag", ["main", "v1", "v2026.11.1; rm -rf /", "../v2026.11.1"])
def test_anything_but_a_release_tag_is_refused(tmp_path, monkeypatch, tag):
    st = world(tmp_path, monkeypatch)
    case_in(tmp_path, "50-release")
    deployed.clear()
    [r] = requests.serve(st, ask(tmp_path, tag=tag), deploy=deploy)
    assert r["outcome"] == "refused" and deployed == []


# --- root runs nothing the runner can write (ADR-028) ---

def _git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x",
                        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "HOME": str(cwd)})


def _code_host(tmp_path: Path) -> Path:
    """A code host with a merged tag on main and a tag on a branch that was never merged."""
    repo = tmp_path / "host"
    repo.mkdir()
    _git("init", "-q", "-b", "main", cwd=repo)
    (repo / "a").write_text("a")
    _git("add", "a", cwd=repo); _git("commit", "-qm", "merged", cwd=repo)
    _git("tag", "-a", "v2026.11.1", "-m", "release", cwd=repo)
    _git("switch", "-qc", "side", cwd=repo)
    (repo / "b").write_text("b")
    _git("add", "b", cwd=repo); _git("commit", "-qm", "never merged", cwd=repo)
    _git("tag", "-a", "v2026.11.2", "-m", "not on main", cwd=repo)
    _git("switch", "-q", "main", cwd=repo)
    return repo


def test_on_main_asks_the_code_host_through_roots_own_mirror(tmp_path):
    from types import SimpleNamespace
    host = _code_host(tmp_path)
    st = SimpleNamespace(server=SimpleNamespace(develop_repo=str(host), runner_user="runner"))
    mirror = tmp_path / "mirror.git"
    assert len(requests.on_main(st, None, "v2026.11.1", mirror=mirror)) == 40
    with pytest.raises(OpsError, match="not on main"):
        requests.on_main(st, None, "v2026.11.2", mirror=mirror)
    assert (mirror / "HEAD").exists()                     # a bare repository of its own, not a stage's checkout


def test_the_service_runs_a_copy_of_the_tool_that_only_its_owner_can_write(tmp_path):
    from pressroom_env import systemd
    source = Path(__file__).resolve().parents[1]
    home = systemd.install_tool(source, tmp_path / "lib")
    pkg = home / "pressroom_env"
    assert (pkg / "requests.py").is_file() and (pkg / "templates" / "deploy-requests.service").is_file()
    assert not list(pkg.rglob("__pycache__"))
    for p in [pkg, *pkg.rglob("*")]:
        assert p.stat().st_mode & 0o022 == 0, f"{p} is writable by group or others"
    r = subprocess.run([sys.executable, "-c", "import pressroom_env.requests as r; print(r.__file__)"], cwd=home,
                       capture_output=True, text=True, check=True)
    assert r.stdout.strip().startswith(str(home))
    systemd.install_tool(source, tmp_path / "lib")        # again: replaced, not nested
    assert not (pkg / "pressroom_env").exists()


# --- a deploy never ends the run that asked for it (ADR-028) ---

def _run_file(tmp_path, space, rid, status):
    d = tmp_path / "srv" / space / "flow" / "_runs"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{rid}.json").write_text(json.dumps({"id": rid, "status": status}), encoding="utf-8")
    return d / f"{rid}.json"


def test_a_deploy_of_the_asking_runs_own_stage_waits_until_the_run_has_ended(tmp_path, monkeypatch):
    st = world(tmp_path, monkeypatch)
    case_in(tmp_path, "50-release", space="shipyard-entw")
    f = _run_file(tmp_path, "shipyard-entw", "rel-1", "running")
    naps = []

    def nap(s):                                                       # the run ends while the service waits
        naps.append(s)
        f.write_text(json.dumps({"id": "rel-1", "status": "done"}), encoding="utf-8")

    monkeypatch.setattr(requests.time, "sleep", nap)
    deployed.clear()
    [r] = requests.serve(st, ask(tmp_path, space_stage="entw", run="rel-1"), deploy=deploy)
    assert naps and r["outcome"] == "deployed" and r["waited_for_run_s"] == 5 and deployed == [("entw", "v2026.11.1")]


def test_a_deploy_to_another_stage_does_not_wait(tmp_path, monkeypatch):
    st = world(tmp_path, monkeypatch)
    case_in(tmp_path, "50-release")
    _run_file(tmp_path, "shipyard", "rel-2", "running")
    monkeypatch.setattr(requests.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("waited")))
    deployed.clear()
    [r] = requests.serve(st, ask(tmp_path, run="rel-2"), deploy=deploy)          # prod space → entw: another runner
    assert r["outcome"] == "deployed" and "waited_for_run_s" not in r
