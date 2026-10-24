"""Agents and sessions in a workspace: components own or shared, rights as an intersection, one session per agent."""

import json
from pathlib import Path

import pytest

from cockpit.agents import AgentError, Catalog, load_agent
from cockpit.sessions import SessionError, Store
from cockpit.workspaces import WorkspaceError, Workspaces


def agent_dir(root: Path, aid: str, spec: dict | None = None, signature: bool = True) -> Path:
    d = root / aid
    d.mkdir(parents=True)
    if signature:
        (d / f"{aid}-signature.md").write_text(f"# {aid}\n", encoding="utf-8")
    if spec is not None:
        (d / "agent.json").write_text(json.dumps(spec), encoding="utf-8")
    return d


@pytest.fixture
def registry(tmp_path):
    shared_agents = tmp_path / "control" / "agents"
    agent_dir(shared_agents, "axel", {"label": "Axel", "skills": ["interpret"], "tools": ["Read", "Grep", "Glob", "Edit", "Write"]})
    agent_dir(shared_agents, "astrid", {"label": "Astrid"})
    agent_dir(shared_agents, "chris")                                   # a human's signature: no agent.json, no agent
    own_agents = tmp_path / "own-agents"
    agent_dir(own_agents, "scout", {"label": "Scout", "tools": ["Read", "WebSearch"], "web": True, "users": ["alex"]})
    reg = {"applications": {"pressroom": {"label": "PressRoom", "config_dir": "config"}},
           "defaults": {"agents": {"path": str(shared_agents), "shared": True, "writable": False}},
           "workspaces": [
               {"id": "team", "application": "pressroom", "shared": True, "root": "team/flow"},
               {"id": "lab", "application": "pressroom", "owner": "alex", "root": "lab/flow",
                "components": {"agents": {"path": str(own_agents)}, "sessions": {"path": "lab/_sessions"}}}]}
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))
    return tmp_path


# ------------------------------------------------------------------- components

def test_components_are_declared_or_default_and_survive_a_save(registry):
    ws = Workspaces(registry / "workspaces.json", registry)
    team, lab = ws.get("team"), ws.get("lab")
    assert ws.component(team, "pipeline").path == registry / "team" / "flow"          # root is the pipeline's older spelling
    assert ws.component(team, "agents").shared and not ws.component(team, "agents").writable
    assert ws.component(team, "sessions").path == registry / "sessions" / "team"      # server-local, beside the registry
    assert ws.component(lab, "agents").path == registry / "own-agents"
    assert ws.component(lab, "sessions").path == registry / "lab" / "_sessions"
    ws.save()
    again = Workspaces(registry / "workspaces.json", registry)
    assert again.component(again.get("lab"), "agents").path == registry / "own-agents"
    assert again.component(again.get("team"), "agents").writable is False
    with pytest.raises(WorkspaceError):
        ws.component(team, "mailbox")


def test_an_unknown_component_in_the_registry_is_refused(registry):
    doc = json.loads((registry / "workspaces.json").read_text())
    doc["workspaces"][0]["components"] = {"inbox": {"path": "x"}}
    (registry / "workspaces.json").write_text(json.dumps(doc))
    with pytest.raises(WorkspaceError, match="not a component"):
        Workspaces(registry / "workspaces.json", registry)


# ------------------------------------------------------------------- agents

def test_each_workspace_offers_its_own_agents_and_who_may_choose_them(registry):
    ws = Workspaces(registry / "workspaces.json", registry)
    team, lab = ws.agents(ws.get("team")), ws.agents(ws.get("lab"))
    assert sorted(team.agents) == ["astrid", "axel"] and sorted(lab.agents) == ["scout"]
    assert team.get("astrid").tools == ("Read", "Grep", "Glob")         # nothing declared: read-only
    assert team.get("astrid").skills == ()
    assert [a.id for a in lab.for_user("alex", "operator")] == ["scout"] and lab.for_user("sam", "operator") == []


def test_rights_are_the_intersection_of_skill_and_agent(registry):
    axel = Workspaces(registry / "workspaces.json", registry).agents(Workspaces(registry / "workspaces.json", registry).get("team")).get("axel")
    skill = {"tools": ["Read", "Edit", "Bash", "WebFetch"], "web": True, "write": ["{container}"], "timeout": 900}
    cut = axel.rules_for(skill)
    assert cut["tools"] == ["Read", "Edit"] and cut["web"] is False and cut["write"] == [] and cut["timeout"] == 900
    assert axel.rules_for(None)["tools"] == ["Read", "Grep", "Glob", "Edit", "Write"]    # a conversation: the ceiling
    assert axel.may_run("interpret") and not axel.may_run("asset")


def test_a_broken_definition_is_reported_and_keeps_the_others(tmp_path):
    agent_dir(tmp_path, "good", {"label": "Good"})
    agent_dir(tmp_path, "bad", {"engine": "telepathy"})
    agent_dir(tmp_path, "evil", {"signature": "../../secrets.env"})
    cat = Catalog.load(tmp_path)
    assert list(cat.agents) == ["good"] and set(cat.problems) == {"bad", "evil"}
    with pytest.raises(AgentError):
        load_agent(tmp_path / "bad")


# ------------------------------------------------------------------- sessions

def test_a_session_runs_from_start_through_messages_to_its_log(tmp_path):
    store = Store(tmp_path / "sessions")
    s, overlap = store.start("lab", "scout", "alex", "Quellen für FN-080 sichten")
    assert overlap == [] and s.id.endswith("_scout_quellen-fuer-fn-080-sichten") and s.starts_from is None
    order = store.say(s.id, "alex", "Was gibt es Neues?")
    assert order["type"] == "chat" and order["session"] == s.id and order["requested_by"] == "alex"
    with pytest.raises(SessionError, match="still answering"):
        store.say(s.id, "alex", "und?")                                           # one message at a time: --resume is a chain
    with pytest.raises(SessionError, match="someone else"):
        store.say(s.id, "sam", "hallo")
    _answer(store, order, "Drei Quellen.")
    store.update(s.id, claude_session="abc-123", turns=1)
    end = store.end(s.id, "alex")
    assert end["type"] == "end" and store.get(s.id).status == "ending"
    with pytest.raises(SessionError, match="ending"):
        store.say(s.id, "alex", "noch was")
    log = store.log_path(store.get(s.id))
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("# log\n", encoding="utf-8")
    _answer(store, end, "Log geschrieben.")
    closed = store.close(s.id, log)
    assert closed.status == "closed" and store.active() == [] and closed.log == "logs/" + log.name
    assert [t["role"] for t in store.transcript(s.id)] == ["user", "assistant", "assistant"]
    nxt, _ = store.start("lab", "scout", "alex", "Weiter")
    assert nxt.starts_from == closed.log                                             # the next session of this agent starts from it
    other, _ = store.start("lab", "axel", "alex", "Weiter")
    assert other.starts_from is None                                                 # another agent's log is not its memory


def test_parallel_sessions_run_and_the_same_key_twice_is_a_warning(tmp_path):
    store = Store(tmp_path)
    a, _ = store.start("lab", "scout", "alex", "Thema")
    b, overlap = store.start("lab", "axel", "alex", "Thema")
    assert overlap == []
    import time; time.sleep(1.01)
    c, overlap = store.start("lab", "scout", "alex", "thema ")
    assert [o.id for o in overlap] == [a.id] and len(store.active()) == 3
    with pytest.raises(SessionError):
        store.start("lab", "scout", "alex", "   ")
    with pytest.raises(SessionError):
        store.get("../../etc/passwd")


def _answer(store: Store, order: dict, text: str) -> None:
    """What the runner does with an order: answer into the transcript, mark the order done."""
    store.add_turn(order["session"], "assistant", text)
    p = store.dir / "queue" / f"{order['id']}.json"
    p.write_text(json.dumps(dict(order, status="done")), encoding="utf-8")


# ------------------------------------------------------------------- the runner serves the session queue

def test_the_runner_answers_resumes_and_closes_a_session_with_its_log(registry, tmp_path):
    import subprocess
    import sys
    from cockpit.account import Accounts
    runner = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline" / "runner.py"
    flow = registry / "lab" / "flow"
    flow.mkdir(parents=True)
    (flow / "run-policy.json").write_text(json.dumps({"default": {"permission_mode": "acceptEdits", "timeout": 60}}))
    accounts = registry / "accounts"
    Accounts(accounts).set_secret("alex", "CLAUDE_CODE_OAUTH_TOKEN", "sk-ant-oat01-" + "x" * 48)
    # a stand-in for claude: echoes the message, remembers the arguments, writes the log when asked to
    seen = tmp_path / "calls.jsonl"
    stub = tmp_path / "claude"
    stub.write_text(f"""#!{sys.executable}
import json, os, re, sys
args = sys.argv[1:]
open({str(seen)!r}, "a").write(json.dumps({{"args": args, "home": os.environ.get("HOME"), "token": "CLAUDE_CODE_OAUTH_TOKEN" in os.environ}}) + "\\n")
prompt = args[args.index("-p") + 1]
m = re.search(r"log to `([^`]+)`", prompt)
if m:
    open(m.group(1), "w").write("# Session log\\n## Continuation Thread\\nweiter\\n")
print(json.dumps({{"result": "echo: " + prompt[:40], "session_id": "cs-1", "total_cost_usd": 0.01, "num_turns": 1, "duration_ms": 900}}))
""")
    stub.chmod(0o755)
    ws = Workspaces(registry / "workspaces.json", registry)
    store = ws.sessions(ws.get("lab"))
    s, _ = store.start("lab", "scout", "alex", "Quellen")
    store.say(s.id, "alex", "Hallo Scout")

    def run_once():
        r = subprocess.run([sys.executable, str(runner), "--workspace", str(tmp_path), "--workspaces", str(registry / "workspaces.json"),
                            "--claude", str(stub), "--accounts", str(accounts), "--context-script", "", "--once"], capture_output=True, text=True)
        assert "Traceback" not in r.stdout + r.stderr, r.stdout + r.stderr
        return r

    run_once()
    turns = store.transcript(s.id)
    assert [t["role"] for t in turns] == ["user", "assistant"] and turns[1]["text"] == "echo: Hallo Scout"
    assert store.get(s.id).claude_session == "cs-1" and store.get(s.id).turns == 1
    store.say(s.id, "alex", "Und weiter?")
    run_once()
    calls = [json.loads(l) for l in seen.read_text().splitlines()]
    assert "--resume" not in calls[0]["args"] and calls[1]["args"][calls[1]["args"].index("--resume") + 1] == "cs-1"
    assert calls[0]["home"] == calls[1]["home"] and calls[0]["token"]                   # one HOME for the session, billed to alex
    allowed = calls[0]["args"][calls[0]["args"].index("--allowedTools") + 1]
    assert allowed == "Read,WebSearch,WebFetch"                                          # scout's ceiling, nothing more
    store.end(s.id, "alex")
    run_once()
    assert store.active() == [] and store.get(s.id).status == "closed"
    log = store.dir / store.get(s.id).log
    assert log.is_file() and "Continuation Thread" in log.read_text()
    assert not Path(calls[0]["home"]).exists()                                           # the session's HOME ended with it
    nxt, _ = store.start("lab", "scout", "alex", "Weiter")
    assert nxt.starts_from == store.get(s.id).log


# ------------------------------------------------------------------- the surface

from tests.test_workspaces import world, sign_in  # noqa: E402,F401 — the cockpit fixture with a shared PressRoom


def test_a_person_picks_an_agent_starts_talks_and_ends_from_the_cockpit(world):
    from fastapi.testclient import TestClient
    from cockpit.app import create_app
    from cockpit.config import load
    agents = world / "agents"
    agent_dir(agents, "axel", {"label": "Axel", "role": "Executor", "tools": ["Read", "Edit"]})
    agent_dir(agents, "astrid", {"label": "Astrid", "users": ["chris"]})          # not alex's to choose
    reg = json.loads((world / "workspaces.json").read_text())
    reg["defaults"] = {"agents": {"path": str(agents), "shared": True}}
    (world / "workspaces.json").write_text(json.dumps(reg))
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    assert client.get("/sessions/shared").status_code in (302, 303)                 # behind the sign-in
    sign_in(client)
    page = client.get("/sessions/shared").text
    assert "Axel" in page and "Astrid" not in page and 'href="/sessions/shared"' in client.get("/").text
    csrf = client.cookies["csrf"]
    r = client.post("/sessions/shared", data={"agent": "astrid", "topic": "x", "_csrf": csrf})
    assert "not%20one%20you%20may%20choose" in r.headers["location"]
    r = client.post("/sessions/shared", data={"agent": "axel", "topic": "Workspace-Agenten testen", "_csrf": csrf})
    loc = r.headers["location"]
    assert r.status_code == 303 and loc.startswith("/sessions/shared/") and "_axel_workspace-agenten-testen" in loc
    assert client.post(loc, data={"what": "say", "text": "Hallo", "_csrf": csrf}).status_code == 303
    state = client.get(loc + "/state").json()
    assert state == {"turns": 1, "pending": True, "status": "active"}
    chat = client.get(loc).text
    assert "Hallo" in chat and "disabled" in chat                                   # one message at a time
    assert "still%20answering" in client.post(loc, data={"what": "say", "text": "noch", "_csrf": csrf}).headers["location"]
    # another person neither sees the conversation nor can write into it
    other = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    sign_in(other, "sam")
    assert other.get(loc + "/state").status_code == 404 and "no%20such%20session" in other.get(loc).headers["location"]
    assert client.get("/sessions/shared/../../etc/state").status_code in (404, 303, 307)


def test_the_conversation_shows_avatars_and_renders_answers_safely(world):
    from fastapi.testclient import TestClient
    from cockpit.app import create_app
    from cockpit.config import load
    agents = world / "agents"
    d = agent_dir(agents, "axel", {"label": "Axel"})
    (d / "axel-avatar.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    agent_dir(agents, "scout", {"label": "Field Scout"})                              # no image: initials
    reg = json.loads((world / "workspaces.json").read_text())
    reg["defaults"] = {"agents": {"path": str(agents)}}
    (world / "workspaces.json").write_text(json.dumps(reg))
    client = TestClient(create_app(load(world / "cockpit.toml")), follow_redirects=False)
    sign_in(client)
    page = client.get("/sessions/shared").text
    assert 'src="/sessions/shared/agent/axel/avatar"' in page and ">FS</span>" in page
    assert client.get("/sessions/shared/agent/axel/avatar").status_code == 200
    assert client.get("/sessions/shared/agent/scout/avatar").status_code == 404
    loc = client.post("/sessions/shared", data={"agent": "axel", "topic": "md", "_csrf": client.cookies["csrf"]}).headers["location"]
    store = Workspaces(world / "workspaces.json", world).sessions(Workspaces(world / "workspaces.json", world).get("shared"))
    store.add_turn(loc.rsplit("/", 1)[1], "assistant", "**fett** und <script>alert(1)</script>")
    html = client.get(loc).text
    assert "<strong>fett</strong>" in html and "<script>alert(1)" not in html and 'id="mic"' in html


def test_an_openai_agent_answers_falls_back_and_learns_into_its_notes(tmp_path):
    import http.server
    import subprocess
    import sys
    import threading
    from cockpit.account import Accounts
    seen = []

    class API(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen.append({"model": body["model"], "auth": self.headers["Authorization"], "n": len(body["input"]), "instructions": body["instructions"][:40]})
            if body["model"] == "big":
                self.send_response(503); self.end_headers(); self.wfile.write(b'{"error": "overloaded"}'); return
            last = body["input"][-1]["content"]
            text = ("# Session\n## Continuation Thread\nweiter\n## Für die Working Notes\nKurze Fragen kurz beantworten." if "End this session" in last
                    else "Hier Atlas: " + last)
            out = {"model": body["model"], "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
                   "usage": {"input_tokens": 10, "output_tokens": 5}}
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(out).encode())

    srv = http.server.HTTPServer(("127.0.0.1", 0), API)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    agents = tmp_path / "agents"
    d = agent_dir(agents, "atlas", {"label": "Atlas", "engine": "openai", "model": "big", "fallback_model": "small"})
    (d / "working-notes.md").write_text("# Atlas — Working Notes\n", encoding="utf-8")
    (tmp_path / "flow").mkdir()
    reg = {"applications": {"pressroom": {"label": "PressRoom", "config_dir": "config"}},
           "workspaces": [{"id": "lab", "application": "pressroom", "owner": "alex", "root": "flow",
                           "components": {"agents": {"path": str(agents)}}}]}
    (tmp_path / "workspaces.json").write_text(json.dumps(reg))
    Accounts(tmp_path / "accounts").set_secret("alex", "OPENAI_API_KEY", "sk-proj-" + "y" * 40)
    ws = Workspaces(tmp_path / "workspaces.json", tmp_path)
    store = ws.sessions(ws.get("lab"))
    s, _ = store.start("lab", "atlas", "alex", "Strategie")
    store.say(s.id, "alex", "Wo stehen wir?")
    runner = Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline" / "runner.py"
    env = dict(__import__("os").environ, OPENAI_BASE_URL=f"http://127.0.0.1:{srv.server_port}")

    def run_once():
        r = subprocess.run([sys.executable, str(runner), "--workspace", str(tmp_path), "--workspaces", str(tmp_path / "workspaces.json"),
                            "--accounts", str(tmp_path / "accounts"), "--context-script", "", "--once"], capture_output=True, text=True, env=env)
        assert "Traceback" not in r.stdout + r.stderr, r.stdout + r.stderr

    run_once()
    assert [x["model"] for x in seen] == ["big", "small"] and seen[0]["auth"] == "Bearer sk-proj-" + "y" * 40
    assert store.transcript(s.id)[-1]["text"] == "Hier Atlas: Wo stehen wir?" and store.transcript(s.id)[-1]["model"] == "small"
    store.end(s.id, "alex")
    run_once()
    closed = store.get(s.id)
    assert closed.status == "closed" and "Continuation Thread" in (store.dir / closed.log).read_text()
    assert "Kurze Fragen kurz beantworten." in (d / "working-notes.md").read_text()          # learned, because the component is writable
    # without a key of their own, nobody's key is used
    s2, _ = store.start("lab", "atlas", "sam", "Ohne Key")
    store.say(s2.id, "sam", "Hallo")
    run_once()
    assert "no OpenAI API key" in store.transcript(s2.id)[-1]["text"] and len(seen) == 4
    srv.shutdown()


def test_what_an_agent_learns_is_committed_to_the_notes_branch_and_never_to_main(tmp_path):
    import importlib.util
    import subprocess
    from types import SimpleNamespace
    git = lambda cwd, *a: subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True).stdout.strip()
    origin, notes_remote = tmp_path / "control.git", tmp_path / "control-notes.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin)); git(tmp_path, "init", "-q", "--bare", "-b", "main", str(notes_remote))
    work = tmp_path / "control"
    git(tmp_path, "clone", "-q", str(origin), str(work))
    d = agent_dir(work / "agents", "atlas", {"label": "Atlas"})
    (d / "working-notes.md").write_text("# notes\n")
    git(work, "add", "-A"); git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base"); git(work, "push", "-q", "origin", "HEAD:main")
    git(work, "remote", "add", "notes", str(notes_remote))
    tree = tmp_path / "notes-entw"
    git(work, "worktree", "add", "-q", "-b", "notes/entw", str(tree), "origin/main")
    spec = importlib.util.spec_from_file_location("runner", Path(__file__).resolve().parents[1] / "cockpit" / "plugins" / "pipeline" / "runner.py")
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    args = SimpleNamespace(notes_repo=tree, notes_remote="notes")
    agent = load_agent(tree / "agents" / "atlas")
    s = SimpleNamespace(id="20261024-170000_atlas_x", topic="Strategie", user="chris")
    assert runner.notes_commit(args, agent, s) is None                                   # nothing learned, nothing committed
    (tree / "agents" / "atlas" / "working-notes.md").write_text("# notes\n### 2026-10-24 — kurz antworten\n")
    sha = runner.notes_commit(args, agent, s)
    assert sha and git(notes_remote, "log", "--format=%an|%s", "notes/entw", "-1") == "Atlas (cockpit)|notes(local): Atlas — Strategie"
    assert git(origin, "log", "--format=%s", "main") == "base"                           # control's main is untouched
    # main moves on; the next turn's sync puts the notes on top of it
    (work / "README.md").write_text("x"); git(work, "add", "-A"); git(work, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "main moves"); git(work, "push", "-q", "origin", "HEAD:main")
    runner.notes_sync(args)
    assert git(tree, "log", "--format=%s", "-2").splitlines() == ["notes(local): Atlas — Strategie", "main moves"]
