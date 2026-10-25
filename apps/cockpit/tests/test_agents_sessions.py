"""Agents belong to the person (ADR-020): templates in the organisation, a team in each account, sessions with a place,
logs in the person's folder — and the engines that run them."""

import http.server
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from cockpit.account import Accounts
from cockpit.agents import AgentError, Catalog, Team, load_agent
from cockpit.sessions import SessionError, Store
from cockpit.workspaces import WorkspaceError, Workspaces

RUNNER = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline" / "runner.py"


def agent_dir(root: Path, aid: str, spec: dict | None = None, signature: bool = True) -> Path:
    d = root / aid
    d.mkdir(parents=True)
    if signature:
        (d / f"{aid}-signature.md").write_text(f"# {aid}\n", encoding="utf-8")
    if spec is not None:
        (d / "agent.json").write_text(json.dumps(spec), encoding="utf-8")
    return d


@pytest.fixture
def org(tmp_path):
    """The organisation's templates and two accounts."""
    t = tmp_path / "org-agents"
    agent_dir(t, "axel", {"label": "Axel", "skills": ["interpret"], "tools": ["Read", "Grep", "Glob", "Edit", "Write"], "web": True})
    agent_dir(t, "atlas", {"label": "Atlas", "engine": "codex", "model": "big", "tools": ["Read"], "users": ["chris"]})
    agent_dir(t, "chris")                                              # a human's signature: no agent.json, no template
    (tmp_path / "accounts").mkdir()
    return tmp_path


def runner(tmp_path, *extra, env=None):
    r = subprocess.run([sys.executable, str(RUNNER), "--workspace", str(tmp_path), "--workspaces", str(tmp_path / "workspaces.json"),
                        "--accounts", str(tmp_path / "accounts"), "--agents", str(tmp_path / "org-agents"),
                        "--context-script", "", "--once", *extra], capture_output=True, text=True, env=env or dict(os.environ, PRESSROOM_ENV="entw"))
    assert "Traceback" not in r.stdout + r.stderr, r.stdout + r.stderr
    return r


def registry(tmp_path, extra=None):
    (tmp_path / "flow").mkdir(exist_ok=True)
    (tmp_path / "flow" / "run-policy.json").write_text(json.dumps({"default": {"permission_mode": "acceptEdits", "timeout": 60}}))
    reg = {"applications": {"pressroom": {"label": "PressRoom", "config_dir": "config"}},
           "workspaces": [{"id": "lab", "application": "pressroom", "owner": "chris", "root": "flow"}, *(extra or [])]}
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))


# ------------------------------------------------------------------- workspace: only the pipeline left

def test_retired_components_are_skipped_and_unknown_ones_refused(tmp_path):
    reg = {"applications": {"pressroom": {"label": "P", "config_dir": "c"}},
           "defaults": {"agents": {"path": "/old"}},
           "workspaces": [{"id": "lab", "application": "pressroom", "root": "flow", "components": {"sessions": {"path": "s"}}}]}
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))
    ws = Workspaces(tmp_path / "workspaces.json", tmp_path)                 # an ADR-019 registry still loads
    assert ws.component(ws.get("lab"), "pipeline").path == tmp_path / "flow"
    with pytest.raises(WorkspaceError):
        ws.component(ws.get("lab"), "agents")
    reg["workspaces"][0]["components"] = {"inbox": {"path": "x"}}
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))
    with pytest.raises(WorkspaceError, match="not a component"):
        Workspaces(tmp_path / "workspaces.json", tmp_path)


# ------------------------------------------------------------------- templates and teams

def test_templates_are_folders_with_a_definition_and_broken_ones_are_reported(tmp_path):
    agent_dir(tmp_path, "good", {"label": "Good"})
    agent_dir(tmp_path, "bad", {"engine": "telepathy"})
    agent_dir(tmp_path, "evil", {"signature": "../../secrets.env"})
    agent_dir(tmp_path, "akhil")
    cat = Catalog.load(tmp_path)
    assert list(cat.agents) == ["good"] and set(cat.problems) == {"bad", "evil"}
    with pytest.raises(AgentError):
        load_agent(tmp_path / "bad")


def test_a_person_hires_from_a_template_and_keeps_their_own_memory(org):
    cat = Catalog.load(org / "org-agents")
    chris, akhil = Team(org / "accounts", "chris", cat, "entw"), Team(org / "accounts", "akhil", cat, "entw")
    assert [t.id for t in chris.hireable("operator")] == ["atlas", "axel"] and [t.id for t in akhil.hireable("operator")] == ["axel"]
    with pytest.raises(AgentError, match="may hire"):
        akhil.hire("atlas", role="operator")                                  # Atlas' profile is Chris' to fill
    a = chris.hire("atlas", role="operator", model="small")
    assert a.template == "atlas" and a.model == "small" and a.engine == "codex" and a.signature_path == org / "org-agents" / "atlas" / "atlas-signature.md"
    assert a.notes_path == org / "accounts" / "chris" / "agents" / "atlas" / "working-notes.md"       # memory in the account
    x1, x2 = chris.hire("axel", role="operator", memory="/srv/{stage}/notes/axel"), akhil.hire("axel", role="operator")
    assert x1.notes_path == Path("/srv/entw/notes/axel/working-notes.md") and x2.notes_path.parent == org / "accounts" / "akhil" / "agents" / "axel"
    with pytest.raises(AgentError, match="already"):
        chris.hire("axel", role="operator")
    # narrower than the template is fine, wider is refused when it loads
    chris.hire("axel", "axel-reader", role="operator", tools=["Read"])
    assert chris.get("axel-reader").tools == ("Read",) and chris.get("axel-reader").skills == ("interpret",)
    with pytest.raises(AgentError, match="more than its template"):
        chris.hire("axel", "axel-bash", role="operator", tools=["Read", "Bash"])
    assert "axel-bash" not in chris.agents and not (chris.dir / "axel-bash" / "agent.json").exists()
    assert chris.dismiss("axel-reader") and "axel-reader" not in chris.agents
    assert any(p.name.startswith("_dismissed-axel-reader-") for p in chris.dir.iterdir())   # memory is not thrown away


def test_rights_are_the_intersection_of_skill_and_agent(org):
    axel = Team(org / "accounts", "chris", Catalog.load(org / "org-agents"), "entw").hire("axel", role="operator")
    skill = {"tools": ["Read", "Edit", "Bash", "WebFetch"], "web": True, "write": ["{container}"], "timeout": 900}
    cut = axel.rules_for(skill)
    assert cut["tools"] == ["Read", "Edit"] and cut["web"] is True and cut["write"] == [] and cut["timeout"] == 900
    assert axel.rules_for(None)["tools"] == ["Read", "Grep", "Glob", "Edit", "Write"]


# ------------------------------------------------------------------- sessions

def _answer(store: Store, order: dict, text: str) -> None:
    store.add_turn(order["session"], "assistant", text)
    p = store.dir / "queue" / f"{order['id']}.json"
    p.write_text(json.dumps(dict(order, status="done")), encoding="utf-8")


def test_a_session_has_a_place_and_its_log_goes_to_the_persons_folder(tmp_path):
    store = Store(tmp_path / "sessions", log_dir=tmp_path / "mine" / "logs")
    s, overlap = store.start("scout", "alex", "Quellen für FN-080 sichten", {"workspace": "lab", "item": "10-ideas/FN-080", "evil": "x"})
    assert overlap == [] and s.place == {"workspace": "lab", "item": "10-ideas/FN-080"} and s.workspace == "lab"
    order = store.say(s.id, "alex", "Was gibt es Neues?")
    assert order["place"]["workspace"] == "lab"
    with pytest.raises(SessionError, match="still answering"):
        store.say(s.id, "alex", "und?")
    with pytest.raises(SessionError, match="someone else"):
        store.say(s.id, "sam", "hallo")
    _answer(store, order, "Drei Quellen.")
    end = store.end(s.id, "alex")
    log = store.log_path(store.get(s.id))
    assert log.parent == tmp_path / "mine" / "logs"
    log.parent.mkdir(parents=True); log.write_text("# log\n")
    _answer(store, end, "Log geschrieben.")
    closed = store.close(s.id, log)
    assert closed.log == str(log) and store.active() == []
    nxt, _ = store.start("scout", "alex", "Weiter")
    assert nxt.starts_from == str(log) and nxt.place == {}
    other, _ = store.start("axel", "alex", "Weiter")
    assert other.starts_from is None


def test_parallel_sessions_and_an_older_record_still_reads(tmp_path):
    store = Store(tmp_path)
    a, _ = store.start("scout", "alex", "Thema")
    b, overlap = store.start("axel", "alex", "Thema")
    assert overlap == []
    time.sleep(1.01)
    c, overlap = store.start("scout", "alex", "thema ")
    assert [o.id for o in overlap] == [a.id] and len(store.active()) == 3
    with pytest.raises(SessionError):
        store.start("scout", "alex", "   ")
    with pytest.raises(SessionError):
        store.get("../../etc/passwd")
    old = {"id": "20261024-120000_axel_alt", "workspace": "pressroom", "agent": "axel", "user": "alex", "topic": "alt",
           "started": "2026-10-24T12:00:00+02:00", "status": "closed", "log": "logs/2026-10-24_alt.md"}
    (tmp_path / "closed").mkdir()
    (tmp_path / "closed" / f"{old['id']}.json").write_text(json.dumps(old))
    s = store.get(old["id"])
    assert s.place == {"workspace": "pressroom"} and s.log == str(tmp_path / "logs" / "2026-10-24_alt.md")


# ------------------------------------------------------------------- the runner serves every person's queue

def test_the_runner_serves_the_persons_team_with_the_pipeline_of_the_place(org):
    registry(org, [{"id": "sams", "application": "pressroom", "owner": "sam", "root": "flow"}])
    accounts = Accounts(org / "accounts")
    accounts.set_secret("chris", "CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-" + "x" * 48)
    accounts.set("chris", "logs_dir", str(org / "notes-{stage}" / "logs"))
    accounts.team("chris", Catalog.load(org / "org-agents"), "entw").hire("axel", role="operator")
    calls = org / "calls.jsonl"
    stub = org / "claude"
    stub.write_text(f"""#!{sys.executable}
import json, os, re, sys
args = sys.argv[1:]
open({str(calls)!r}, "a").write(json.dumps({{"args": args, "home": os.environ.get("HOME"), "data": os.environ.get("COCKPIT_DATA_DIR"),
    "pressroom": os.path.islink(os.path.join(os.getcwd(), "pressroom"))}}) + "\\n")
prompt = args[args.index("-p") + 1]
m = re.search(r"log to `([^`]+)`", prompt)
if m:
    open(m.group(1), "w").write("# Session log\\n## Continuation Thread\\nweiter\\n")
print(json.dumps({{"result": "echo: " + prompt[:40], "session_id": "cs-1", "total_cost_usd": 0.01, "num_turns": 1, "duration_ms": 900}}))
""")
    stub.chmod(0o755)
    store = accounts.store("chris", "entw")
    s, _ = store.start("axel", "chris", "Mit Pipeline", {"workspace": "lab"})
    store.say(s.id, "chris", "Hallo Axel")
    runner(org, "--claude", str(stub))
    assert [t["role"] for t in store.transcript(s.id)] == ["user", "assistant"] and store.get(s.id).claude_session == "cs-1"
    c = [json.loads(l) for l in calls.read_text().splitlines()]
    assert c[0]["data"] == str(org / "flow") and c[0]["pressroom"]                        # the place gives the pipeline
    allowed = c[0]["args"][c[0]["args"].index("--allowedTools") + 1]
    assert allowed == "Read,Grep,Glob,Edit,Write,WebFetch,WebSearch"
    store.end(s.id, "chris")
    runner(org, "--claude", str(stub))
    closed = store.get(s.id)
    assert closed.status == "closed" and Path(closed.log).parent == org / "notes-entw" / "logs"   # the person's own folder
    # a place the person may not open gives no pipeline
    s2, _ = store.start("axel", "chris", "Fremder Ort", {"workspace": "sams"})
    store.say(s2.id, "chris", "Und hier?")
    runner(org, "--claude", str(stub))
    last = json.loads(calls.read_text().splitlines()[-1])
    assert last["data"] is None and not last["pressroom"]
    # an agent not on the person's team does not run
    store2 = accounts.store("sam", "entw")
    s3, _ = store2.start("axel", "sam", "Ohne Team")
    store2.say(s3.id, "sam", "Hallo")
    runner(org, "--claude", str(stub))
    order = json.loads(next((store2.dir / "queue").glob("*.json")).read_text())
    assert order["status"] == "failed" and "not on sam's team" in order["result"]


def test_an_openai_agent_answers_falls_back_and_learns_into_its_notes(org):
    seen = []

    class API(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append(body["model"])
            if body["model"] == "big":
                self.send_response(503); self.end_headers(); self.wfile.write(b'{"error": "overloaded"}'); return
            last = body["input"][-1]["content"]
            text = ("# Session\n## Continuation Thread\nweiter\n## Für die Working Notes\nKurze Fragen kurz beantworten."
                    if "End this session" in last else "Hier Atlas: " + last)
            out = {"model": body["model"], "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]}
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(out).encode())

    srv = http.server.HTTPServer(("127.0.0.1", 0), API)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    registry(org)
    (org / "org-agents" / "atlas" / "agent.json").write_text(json.dumps({"label": "Atlas", "engine": "openai", "model": "big", "fallback_model": "small"}))
    accounts = Accounts(org / "accounts")
    accounts.set_secret("chris", "OPENAI_API_KEY", "sk-proj-" + "y" * 40)
    atlas = accounts.team("chris", Catalog.load(org / "org-agents"), "entw").hire("atlas", role="operator")
    store = accounts.store("chris", "entw")
    s, _ = store.start("atlas", "chris", "Strategie")
    store.say(s.id, "chris", "Wo stehen wir?")
    env = dict(os.environ, PRESSROOM_ENV="entw", OPENAI_BASE_URL=f"http://127.0.0.1:{srv.server_port}")
    runner(org, env=env)
    assert seen == ["big", "small"] and store.transcript(s.id)[-1]["text"] == "Hier Atlas: Wo stehen wir?"
    store.end(s.id, "chris")
    runner(org, env=env)
    assert store.get(s.id).status == "closed" and "Kurze Fragen kurz beantworten." in atlas.notes_path.read_text()
    srv.shutdown()


def test_a_codex_agent_runs_on_the_persons_plan_and_resumes_its_thread(org):
    calls = org / "codex-calls.jsonl"
    stub = org / "codex"
    stub.write_text(f"""#!{sys.executable}
import json, os, re, sys
a = sys.argv[1:]
open({str(calls)!r}, "a").write(json.dumps({{"args": a, "home": os.environ.get("CODEX_HOME"), "key": "CODEX_API_KEY" in os.environ}}) + "\\n")
prompt = a[-1]
m = re.search(r"log to `([^`]+)`", prompt)
if m:
    open(m.group(1), "w").write("# Session\\n## Continuation Thread\\nweiter\\n")
open(a[a.index("-o") + 1], "w").write("Codex-Atlas: " + prompt[-20:])
print(json.dumps({{"type": "thread.started", "thread_id": "th-42"}}))
print(json.dumps({{"type": "turn.completed", "usage": {{"input_tokens": 7, "output_tokens": 3}}}}))
""")
    stub.chmod(0o755)
    registry(org)
    plan = org / "accounts" / "chris" / "codex"
    plan.mkdir(parents=True)
    (plan / "auth.json").write_text("{}")
    accounts = Accounts(org / "accounts")
    accounts.team("chris", Catalog.load(org / "org-agents"), "entw").hire("atlas", role="operator")
    store = accounts.store("chris", "entw")
    s, _ = store.start("atlas", "chris", "Codex", {"workspace": "lab"})
    store.say(s.id, "chris", "Erste Frage")
    runner(org, "--codex", str(stub))
    store.say(s.id, "chris", "Zweite Frage")
    runner(org, "--codex", str(stub))
    c = [json.loads(l) for l in calls.read_text().splitlines()]
    assert c[0]["home"] == str(plan) and not c[0]["key"] and c[0]["args"][c[0]["args"].index("-m") + 1] == "big"
    assert "resume" not in c[0]["args"] and c[1]["args"][c[1]["args"].index("resume") + 1] == "th-42"
    store.end(s.id, "chris")
    runner(org, "--codex", str(stub))
    assert store.get(s.id).status == "closed" and Path(store.get(s.id).log).is_file()


def test_memory_and_log_inside_the_notes_worktree_become_one_commit_never_on_main(tmp_path):
    import importlib.util
    from types import SimpleNamespace
    git = lambda cwd, *a: subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True).stdout.strip()
    origin, notes_remote = tmp_path / "control.git", tmp_path / "control-notes.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin)); git(tmp_path, "init", "-q", "--bare", "-b", "main", str(notes_remote))
    work = tmp_path / "control"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "agents" / "atlas").mkdir(parents=True); (work / "agents" / "atlas" / "working-notes.md").write_text("# notes\n")
    git(work, "add", "-A"); git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"); git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "remote", "add", "notes", str(notes_remote))
    tree = tmp_path / "notes-entw"
    git(work, "worktree", "add", "-q", "-b", "notes/entw", str(tree), "origin/main")
    spec = importlib.util.spec_from_file_location("runner", RUNNER)
    runner_mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner_mod)
    args = SimpleNamespace(notes_repo=tree, notes_remote="notes")
    s = SimpleNamespace(id="20261025-170000_atlas_x", topic="Strategie", user="chris")
    notes = tree / "agents" / "atlas" / "working-notes.md"
    log = tree / "context" / "session-logs" / "cockpit" / "2026-10-25_strategie.md"
    assert runner_mod.notes_commit(args, "Atlas", s, [notes, None]) is None              # nothing learned, nothing committed
    notes.write_text("# notes\n### 2026-10-25 — kurz antworten\n")
    log.parent.mkdir(parents=True); log.write_text("# Session\n")
    sha = runner_mod.notes_commit(args, "Atlas", s, [notes, log, tmp_path / "elsewhere.md"])
    assert sha and git(notes_remote, "log", "--format=%an|%s", "notes/entw", "-1") == "Atlas (cockpit)|notes(local): Atlas — Strategie"
    assert git(notes_remote, "show", "--stat", "--format=", "notes/entw").count("|") == 2         # memory and log, one commit
    assert git(origin, "log", "--format=%s", "main") == "base"
    (work / "README.md").write_text("x"); git(work, "add", "-A"); git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "main moves"); git(work, "push", "-q", "origin", "HEAD:main")
    runner_mod.notes_sync(args)
    assert git(tree, "log", "--format=%s", "-2").splitlines() == ["notes(local): Atlas — Strategie", "main moves"]


# ------------------------------------------------------------------- the surface

from tests.test_workspaces import world, sign_in  # noqa: E402,F401 — the cockpit fixture with a shared PressRoom


def _cockpit(world):
    from fastapi.testclient import TestClient
    from cockpit.app import create_app
    from cockpit.config import load
    org = world / "org-agents"
    d = agent_dir(org, "axel", {"label": "Axel", "role": "Executor", "tools": ["Read", "Edit"]})
    from PIL import Image
    Image.new("RGB", (600, 400), "red").save(d / "axel-avatar.png")
    agent_dir(org, "atlas", {"label": "Atlas", "users": ["chris"]})
    toml = (world / "cockpit.toml").read_text(encoding="utf-8")
    (world / "cockpit.toml").write_text(toml.replace('[cockpit]\n', '[cockpit]\nagents = "org-agents"\n', 1), encoding="utf-8")
    return TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)


def test_a_person_hires_and_talks_to_their_team_from_any_page(world):
    client = _cockpit(world)
    assert client.get("/team").status_code in (302, 303)
    sign_in(client)
    page = client.get("/team").text
    assert "Axel" in page and "Atlas" not in page and "agent-panel.js" in page
    csrf = client.cookies["csrf"]
    r = client.post("/team", data={"what": "hire", "template": "atlas", "_csrf": csrf})
    assert "may%20hire" in r.headers["location"]
    assert client.post("/team", data={"what": "hire", "template": "axel", "_csrf": csrf}).status_code == 303
    team = client.get("/api/team").json()
    assert [a["id"] for a in team["agents"]] == ["axel"] and team["agents"][0]["img"]
    av = client.get("/api/agents/axel/avatar")
    assert av.headers["content-type"] == "image/webp" and len(av.content) < 5000
    assert client.post("/api/sessions", json={"agent": "axel", "topic": "x"}).status_code == 403          # no CSRF header
    h = {"X-CSRF": csrf}
    r = client.post("/api/sessions", json={"agent": "axel", "topic": "Workspace-Agenten testen",
                                           "place": {"workspace": "shared", "item": "10-ideas/X", "url": "/w/shared/"}}, headers=h)
    sid = r.json()["id"]
    v = client.get(f"/api/sessions/{sid}").json()
    assert v["place"] == {"workspace": "shared", "item": "10-ideas/X", "url": "/w/shared/"} and v["status"] == "active"
    assert client.post(f"/api/sessions/{sid}/say", json={"text": "Hallo"}, headers=h).json() == {"ok": True}
    v = client.get(f"/api/sessions/{sid}").json()
    assert v["pending"] == "chat" and v["turns"][0]["text"] == "Hallo"
    assert "still answering" in client.post(f"/api/sessions/{sid}/say", json={"text": "noch"}, headers=h).json()["reason"]
    # a workspace the person cannot open is dropped from the place
    reg = json.loads((world / "workspaces.json").read_text())
    reg["workspaces"].append({"id": "sams", "application": "pressroom", "owner": "sam", "root": reg["workspaces"][0]["root"]})
    (world / "workspaces.json").write_text(json.dumps(reg))
    client2 = _restart(world)
    sign_in(client2)
    r = client2.post("/api/sessions", json={"agent": "axel", "topic": "fremd", "place": {"workspace": "sams"}}, headers={"X-CSRF": client2.cookies["csrf"]})
    assert client2.get(f"/api/sessions/{r.json()['id']}").json()["place"] == {}
    # the panel stands beside the person inside the mounted applications too
    assert "agent-panel.js" in client.get("/w/shared/").text
    # another person neither sees the session nor has the team
    other = _restart(world)
    sign_in(other, "sam")
    assert other.get(f"/api/sessions/{sid}").status_code == 404 and other.get("/api/team").json()["agents"] == []
    store_page = client.get(f"/sessions/{sid}").text
    assert "Workspace-Agenten testen" in store_page


def test_answers_render_as_markdown_and_raw_html_stays_text(world):
    client = _cockpit(world)
    sign_in(client)
    client.post("/team", data={"what": "hire", "template": "axel", "_csrf": client.cookies["csrf"]})
    sid = client.post("/api/sessions", json={"agent": "axel", "topic": "md"}, headers={"X-CSRF": client.cookies["csrf"]}).json()["id"]
    store = Accounts(world / "accounts").store("alex", "prod")           # no environment set: the stage is prod
    store.add_turn(sid, "assistant", "**fett** und <script>alert(1)</script>")
    v = client.get(f"/api/sessions/{sid}").json()
    assert "<strong>fett</strong>" in v["turns"][-1]["html"] and "<script>alert(1)" not in v["turns"][-1]["html"]
    assert "<strong>fett</strong>" in client.get(f"/sessions/{sid}").text


def _restart(world):
    from fastapi.testclient import TestClient
    from cockpit.app import create_app
    from cockpit.config import load
    return TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
