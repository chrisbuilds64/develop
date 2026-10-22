"""The core's API (Bauplan §4). JSON in, JSON out; the surface is static files served beside it (ADR-014).

Every request leaves one audit line in `<root>/_audit/api.jsonl`. Identity is a signed cookie naming a
person from people.json; how it is obtained depends on the deployment (open in development and in the
demo sandbox, a login later). The core recovers half-done steps on start and records manual moves on read.

Two ways to run it:
- **one pipeline** (`Settings.root` + `config_dir`): the real thing, one store, one configuration;
- **the public demo** (`Settings.worlds`): every visitor gets a sandbox, a fresh copy of a world's template
  under `sessions_dir/<id>/`, bound to a signed cookie (ADR-016). "Start over" makes a new one. Old
  sandboxes are swept; a cap removes the oldest first; a per-IP limit protects the host.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import shutil

from ..demo.sandbox import copy_world
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__
from ..config import DomainConfig
from ..domain import assets, cases as reading, step as stepping
from ..domain import turn as whose
from ..models import Case, StepRequest, StepResult, Turn
from ..store import FsStore, StoreError
from . import views

COOKIE = "cf_person"
DEMO_COOKIE = "cf_demo"
LANG_COOKIE = "cf_lang"           # the viewer's language, when it differs from the world's; plain, not secret


@dataclass
class World:
    config_dir: Path
    template: Path                               # a built pipeline root to copy per visitor
    person: str                                  # the visitor's identity in this world
    lang: str | None = None


@dataclass
class Settings:
    root: Path | None = None                     # one pipeline: the root
    config_dir: Path | None = None               # one pipeline: config/<domain>
    lang: str | None = None
    open_identity: bool = True                   # POST /api/session {person} without a password (development, demo)
    secret: str = field(default_factory=lambda: secrets.token_hex(16))
    web_dist: Path | None = None                 # the built surface, served at /
    max_upload_mb: int = 10
    recover_on_start: bool = True
    demo: bool = False                           # samples offered, prepared replies played back
    samples_dir: Path | None = None
    replies_dir: Path | None = None
    worlds: dict[str, World] = field(default_factory=dict)      # the public demo: name → world
    default_world: str = "claims"
    sessions_dir: Path | None = None
    session_hours: int = 24
    session_cap: int = 500
    rate_per_minute: int = 1200                  # requests per IP and minute — a room shares one Wi-Fi address
    sessions_per_minute: int = 60                # new sandboxes per IP and minute


class SessionIn(BaseModel):
    person: str


class LangIn(BaseModel):
    lang: str


class DemoSessionIn(BaseModel):
    world: str | None = None


class EntryIn(BaseModel):
    kind: str = "note"                           # note | answer | done
    step_id: str
    text: str = ""
    for_: str | None = Field(default=None, alias="for")
    resolves: str | None = None
    title: str | None = None

    model_config = {"populate_by_name": True}


class RunIn(BaseModel):
    skill: str = "ask"
    note: str = ""
    request_id: str


class SampleIn(BaseModel):
    slot: str
    step_id: str


class MeOut(BaseModel):
    person: str | None
    name: str | None
    roles: list[str]
    lang: str
    product: str
    demo: bool
    world: str | None
    worlds: list[str]


class TurnOut(BaseModel):
    case: views.CaseCard
    turn: Turn


class GroupOut(BaseModel):
    key: str
    word: str
    cases: list[views.CaseCard]


class StageOut(BaseModel):
    folder: str
    key: str
    word: str
    station: str = ""                                     # the station's word, for column headers
    cases: list[views.CaseCard]


class RuleAction(BaseModel):
    id: str
    word: str
    to_word: str = ""
    run: str = ""
    requires: list[str] = []


class RuleAuto(BaseModel):
    on_file: str
    skill: str


class RuleStage(BaseModel):
    folder: str
    station: str
    word: str
    turn_word: str
    actions: list[RuleAction]
    auto: list[RuleAuto]


class RuleSkill(BaseModel):
    name: str
    does: str = ""
    never: str = ""
    rules: list[str] = []
    orderable_by: list[str] = []


class RuleModule(BaseModel):
    id: str
    kind: str
    title: str
    version: int
    status: str
    approved_by: str
    date: str
    text: str


class RuleConnector(BaseModel):
    id: str
    name: str
    standard: str = ""
    carries: str = ""
    direction: str = ""
    note: str = ""


class SignalCase(BaseModel):
    id: str
    title: str
    external_id: str = ""
    stage_word: str = ""


class SignalOut(BaseModel):
    """A hint the pattern helper found across files: never a finding, always with its reasoning and the files it rests on."""
    id: str
    kind: str
    title: str
    status: str
    date: str
    cases: list[SignalCase]
    text: str


class RulesOut(BaseModel):
    """The rulebook: stages and gates, what each helper does and never does, the approved modules and rules with versions, the connectors."""
    stages: list[RuleStage]
    skills: list[RuleSkill]
    modules: list[RuleModule]
    connectors: list[RuleConnector] = []


class AssetOut(BaseModel):
    name: str
    slot: str
    step: StepResult


@dataclass
class Ctx:
    store: FsStore
    config: DomainConfig
    lang: str
    world: str | None = None
    session: str | None = None


def _sign(secret: str, value: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Limiter:
    """A small per-key sliding window; enough to keep one host alive under a room full of phones."""

    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] < now - window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="casefile", version=__version__, description=__doc__)
    app.state.settings = settings
    limiter = Limiter()
    single: Ctx | None = None
    if settings.root is not None and settings.config_dir is not None:
        store = FsStore(settings.root)
        config = DomainConfig.load(settings.config_dir, settings.root)
        single = Ctx(store=store, config=config, lang=settings.lang or config.lang)
        if settings.recover_on_start:
            stepping.recover(store, config)
    world_configs: dict[str, DomainConfig] = {name: DomainConfig.load(w.config_dir, w.template) for name, w in settings.worlds.items()}
    sessions: dict[str, Ctx] = {}
    sessions_lock = threading.Lock()
    if settings.worlds:
        settings.sessions_dir.mkdir(parents=True, exist_ok=True)
    def samples_of(c: Ctx) -> tuple[Path | None, list[str]]:
        """The world's own samples (`_samples/` at the pipeline root) win over the ones bundled with the package."""
        own = c.store.root / "_samples"
        d = own if own.is_dir() else settings.samples_dir
        return (d, sorted(p.name for p in d.iterdir() if p.is_file())) if d and d.is_dir() else (None, [])

    # ------------------------------------------------------------ sandboxes
    def _session_ctx(sid: str) -> Ctx | None:
        with sessions_lock:
            if sid in sessions:
                return sessions[sid]
        d = settings.sessions_dir / sid
        if not d.is_dir():
            return None
        try:
            world = (d / ".world").read_text(encoding="utf-8").strip()
            w = settings.worlds[world]
        except (OSError, KeyError):
            return None
        ctx = Ctx(store=FsStore(d / "flow"), config=DomainConfig.load(w.config_dir, d / "flow"), lang=w.lang or world_configs[world].lang, world=world, session=sid)
        with sessions_lock:
            sessions[sid] = ctx
        return ctx

    def _new_session(world: str) -> Ctx:
        w = settings.worlds[world]
        sid = secrets.token_urlsafe(12)
        d = settings.sessions_dir / sid
        copy_world(w.template, d / "flow")
        (d / ".world").write_text(world, encoding="utf-8")
        (d / ".created").write_text(_now(), encoding="utf-8")
        _sweep()
        return _session_ctx(sid)

    def _sweep() -> int:
        """Old sandboxes go; above the cap, the oldest go first."""
        if not settings.worlds:
            return 0
        now = time.time()
        gone = 0
        for p in [p for p in settings.sessions_dir.iterdir() if p.is_dir() and (p / ".created").is_file()]:
            if now - p.stat().st_mtime > settings.session_hours * 3600 and now - (p / ".created").stat().st_mtime > settings.session_hours * 3600:
                shutil.rmtree(p, ignore_errors=True)
                gone += 1
        dirs = sorted((p for p in settings.sessions_dir.iterdir() if p.is_dir() and (p / ".created").is_file()), key=lambda p: (p / ".created").stat().st_mtime)
        while len(dirs) > settings.session_cap:
            shutil.rmtree(dirs.pop(0), ignore_errors=True)
            gone += 1
        with sessions_lock:
            for sid in list(sessions):
                if not (settings.sessions_dir / sid).is_dir():
                    sessions.pop(sid, None)
        return gone

    app.state.sweep = _sweep
    app.state.sessions = sessions

    if settings.demo and settings.replies_dir:
        from ..demo.replay import ReplayRunner

        def roots():
            with sessions_lock:
                live = list(sessions.values())
            return [(c.store, c.config) for c in ([single] if single else []) + live]
        app.state.replay = ReplayRunner(roots, settings.replies_dir).start()

    # ------------------------------------------------------------ resolving a request
    def _who(request: Request, config: DomainConfig) -> str | None:
        raw = request.cookies.get(COOKIE, "")
        if "." not in raw:
            return None
        person, sig = raw.rsplit(".", 1)
        p = config.person(person) if hmac.compare_digest(sig, _sign(settings.secret, person)) else None
        return p.id if p else None

    def _client(request: Request) -> str:
        return request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0].strip()

    def _set_person(response: Response, person_id: str) -> None:
        response.set_cookie(COOKIE, f"{person_id}.{_sign(settings.secret, person_id)}", httponly=True, samesite="lax", max_age=30 * 24 * 3600)

    def _set_session(response: Response, sid: str) -> None:
        response.set_cookie(DEMO_COOKIE, f"{sid}.{_sign(settings.secret, sid)}", httponly=True, samesite="lax", max_age=settings.session_hours * 3600)

    def ctx(request: Request, response: Response) -> Ctx:
        """The store and configuration this request works on, in the viewer's language if they chose one the domain speaks."""
        c = _ctx(request, response)
        lang = request.cookies.get(LANG_COOKIE, "")
        return replace(c, lang=lang) if lang and lang != c.lang and lang in c.config.vocabulary else c

    def _ctx(request: Request, response: Response) -> Ctx:
        """In the demo, a missing sandbox is created on the spot."""
        if not limiter.allow(_client(request), settings.rate_per_minute):
            raise HTTPException(429, "too many requests")
        if single is not None and not settings.worlds:
            return single
        raw = request.cookies.get(DEMO_COOKIE, "")
        if "." in raw:
            sid, sig = raw.rsplit(".", 1)
            if hmac.compare_digest(sig, _sign(settings.secret, sid)):
                c = _session_ctx(sid)
                if c is not None:
                    return c
        if not limiter.allow("new:" + _client(request), settings.sessions_per_minute):
            raise HTTPException(429, "too many new sessions")
        c = _new_session(settings.default_world)
        _set_session(response, c.session)
        _set_person(response, settings.worlds[c.world].person)
        request.state.fresh_person = settings.worlds[c.world].person
        return c

    def viewer(request: Request, c: Ctx = Depends(ctx)) -> str:
        who = getattr(request.state, "fresh_person", None) or _who(request, c.config)
        if not who:
            raise HTTPException(401, "not signed in")
        return who

    def product(c: Ctx) -> str:
        v = c.config.vocabulary.get(c.lang) or c.config.vocabulary.get("en") or {}
        return str(v.get("product") or c.config.name)

    def me_out(c: Ctx, person_id: str | None) -> MeOut:
        p = c.config.person(person_id) if person_id else None
        return MeOut(person=p.id if p else None, name=p.name if p else None, roles=p.roles if p else [], lang=c.lang, product=product(c),
                     demo=settings.demo, world=c.world, worlds=list(settings.worlds))

    # ------------------------------------------------------------ audit, one line per request
    @app.middleware("http")
    async def audit(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            line = {"at": _now(), "who": "-", "method": request.method, "path": request.url.path, "status": response.status_code,
                    "ms": round((time.perf_counter() - t0) * 1000), "ip": _client(request)}
            target = single
            raw = request.cookies.get(DEMO_COOKIE, "")
            if settings.worlds and "." in raw:
                target = _session_ctx(raw.rsplit(".", 1)[0])
            if target is not None:
                line["who"] = _who(request, target.config) or "-"
                try:
                    target.store.append("_audit/api.jsonl", json.dumps(line, ensure_ascii=False) + "\n")
                except OSError:
                    pass
        return response

    # ------------------------------------------------------------ session
    @app.post("/api/session", response_model=MeOut)
    def session(body: SessionIn, response: Response, c: Ctx = Depends(ctx)):
        if not settings.open_identity:
            raise HTTPException(403, "this deployment does not accept an open identity")
        p = c.config.person(body.person)
        if p is None or p.kind != "human":
            raise HTTPException(404, f"'{body.person}' is not a person here")
        _set_person(response, p.id)
        return me_out(c, p.id)

    @app.delete("/api/session")
    def end_session(response: Response):
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.post("/api/session/lang")
    def set_lang(body: LangIn, response: Response, c: Ctx = Depends(ctx)):
        """The viewer's language, kept in a cookie for a year; only languages the domain's vocabulary speaks."""
        if body.lang not in c.config.vocabulary:
            raise HTTPException(400, f"no vocabulary for '{body.lang}'; the domain speaks {', '.join(k for k in c.config.vocabulary if not k.startswith('$'))}")
        response.set_cookie(LANG_COOKIE, body.lang, samesite="lax", max_age=365 * 24 * 3600)
        return {"ok": True, "lang": body.lang}

    @app.post("/api/demo/session", response_model=MeOut)
    def demo_session(response: Response, request: Request, body: DemoSessionIn | None = None):
        """A fresh sandbox: start over, or switch to the other world."""
        if not settings.worlds:
            raise HTTPException(404, "not a demo")
        if not limiter.allow("new:" + _client(request), settings.sessions_per_minute):
            raise HTTPException(429, "too many new sessions")
        world = (body.world if body and body.world else None) or settings.default_world
        if world not in settings.worlds:
            raise HTTPException(404, f"no world '{world}'")
        c = _new_session(world)
        _set_session(response, c.session)
        _set_person(response, settings.worlds[world].person)
        return me_out(c, settings.worlds[world].person)

    @app.get("/api/me", response_model=MeOut)
    def me(request: Request, c: Ctx = Depends(ctx)):
        return me_out(c, getattr(request.state, "fresh_person", None) or _who(request, c.config))

    # ------------------------------------------------------------ reading
    @app.get("/api/config", response_model=views.ConfigView)
    def get_config(c: Ctx = Depends(ctx)):
        v = views.config_view(c.config, c.lang)
        v.theme = {**v.theme, "demo": settings.demo, "samples": samples_of(c)[1] if settings.demo else [], "world": c.world, "worlds": list(settings.worlds)}
        return v

    @app.get("/api/me/turns", response_model=list[TurnOut])
    def my_turns(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        stepping.detect(c.store, c.config)
        all_cases = reading.load_all(c.store, c.config)
        return [TurnOut(case=views.card(c.config, case, who, c.lang), turn=t) for case, t in whose.turns_for(who, all_cases, c.config, c.lang)]

    @app.get("/api/cases", response_model=list[GroupOut])
    def list_cases(group: str | None = None, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        stepping.detect(c.store, c.config)
        cards = [views.card(c.config, case, who, c.lang) for case in reading.load_all(c.store, c.config)]
        order = ["you", "claude", "others", "date", "planned", "out", "ideas", "archive"]
        out = []
        for g in order:
            if group and g != group:
                continue
            mine = [x for x in cards if x.group == g]
            if g == "out":
                mine.sort(key=lambda x: x.date, reverse=True)
            else:
                mine.sort(key=lambda x: x.since)
            out.append(GroupOut(key=g, word=c.config.word("groups", g, c.lang, g), cases=mine))
        return out

    def file_url(case: Case, name: str) -> str:
        return f"/api/cases/{case.id}/files/{name}"

    @app.get("/api/cases/{case_id}", response_model=views.CaseView)
    def get_case(case_id: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        try:
            case = reading.load(c.store, c.config, case_id)
        except (KeyError, StoreError) as exc:
            raise HTTPException(404, str(exc) or case_id)
        return views.view(c.config, case, who, c.lang, file_url)

    @app.get("/api/cases/{case_id}/files/{name}")
    def get_file(case_id: str, name: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        if "/" in name or name.startswith("."):
            raise HTTPException(404, name)
        try:
            p = c.store.case_dir(case_id) / name
        except StoreError:
            raise HTTPException(404, case_id)
        if not p.is_file():
            raise HTTPException(404, name)
        return FileResponse(p)

    @app.get("/api/cases/{case_id}/read/{name}")
    def read_file(case_id: str, name: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """A text file rendered for the viewer: {kind, html}. Images and PDFs come from /files."""
        from .text import render
        if "/" in name or name.startswith("."):
            raise HTTPException(404, name)
        try:
            p = c.store.case_dir(case_id) / name
        except StoreError:
            raise HTTPException(404, case_id)
        if not p.is_file():
            raise HTTPException(404, name)
        ext = name.rsplit(".", 1)[-1].lower()
        if ext not in ("md", "txt", "json"):
            raise HTTPException(415, "not a text file")
        kind = "md" if ext == "md" else "plain"
        return {"name": name, "kind": kind, "html": render(p.read_text(encoding="utf-8", errors="replace"), kind)}

    @app.get("/api/signals", response_model=list[SignalOut])
    def get_signals(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """What the pattern helper noticed across the files of this world: `_signale/*.md` at the pipeline root."""
        folder = c.store.root / "_signale"
        if not folder.is_dir():
            return []
        titles = {case.id: (str(case.meta.get("title") or case.id), str(case.meta.get("external_id") or ""), c.config.word("stages", case.stage, c.lang, case.stage))
                  for case in reading.load_all(c.store, c.config)}
        out = []
        for f in sorted(folder.glob("*.md"), reverse=True):
            text = f.read_text(encoding="utf-8")
            head, body = {}, text
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) == 3:
                    for line in parts[1].splitlines():
                        if ":" in line:
                            k, v = line.split(":", 1)
                            head[k.strip()] = v.strip()
                    body = parts[2]
            ids = [x.strip() for x in head.get("cases", "").split(",") if x.strip()]
            out.append(SignalOut(id=head.get("id", f.stem), kind=head.get("kind", ""), title=head.get("title", f.stem), status=head.get("status", "offen"), date=head.get("date", ""),
                                 cases=[SignalCase(id=i, title=titles.get(i, (i, "", ""))[0], external_id=titles.get(i, (i, "", ""))[1], stage_word=titles.get(i, (i, "", ""))[2]) for i in ids],
                                 text=body.strip()))
        return out

    @app.get("/api/rules", response_model=RulesOut)
    def get_rules(c: Ctx = Depends(ctx)):
        """The rulebook of this world: read from the configuration and from `_bausteine/` at the pipeline root."""
        lang = c.lang

        def actor_word(actor: str | None) -> str:
            if not actor:
                return ""
            if actor == "claude":
                return next((p.name for p in c.config.people if p.kind == "agent"), "KI")
            if actor.startswith("role:"):
                return c.config.word("roles", actor[5:], lang, actor[5:])
            return next((p.name for p in c.config.people if p.id == actor), actor)

        stages = []
        for st in c.config.stages:
            if st.group == "archive":
                continue
            stages.append(RuleStage(folder=st.folder, station=c.config.word("stations", st.key, lang, "") if st.key else "", word=c.config.word("stages", st.folder, lang, st.folder),
                                    turn_word=actor_word(st.turn),
                                    actions=[RuleAction(id=a.id, word=c.config.word("actions", a.id, lang, a.id), to_word=c.config.word("stages", a.to, lang, a.to) if a.to else "",
                                                        run=a.run or "", requires=[c.config.word("files", r, lang, r) if not r.startswith("shape:") else r for r in (a.requires or [])]) for a in st.actions],
                                    auto=[RuleAuto(on_file=c.config.word("files", r.on_file, lang, r.on_file), skill=r.skill) for r in (st.auto or [])]))
        policy = c.config.run_policy or {}
        default = policy.get("default", {})
        skills = [RuleSkill(name=name, does=str(spec.get("does", "")), never=str(spec.get("never", "")), rules=list(spec.get("rules", [])),
                            orderable_by=[c.config.word("roles", r, lang, r) for r in spec.get("orderable_by", default.get("orderable_by", []))])
                  for name, spec in policy.get("skills", {}).items() if not name.startswith("$")]
        modules = []
        folder = c.store.root / "_bausteine"
        if folder.is_dir():
            for f in sorted(folder.glob("*.md")):
                text = f.read_text(encoding="utf-8")
                head, body = {}, text
                if text.startswith("---"):
                    parts = text.split("---", 2)
                    if len(parts) == 3:
                        for line in parts[1].splitlines():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                head[k.strip()] = v.strip()
                        body = parts[2]
                modules.append(RuleModule(id=head.get("id", f.stem), kind=head.get("kind", ""), title=head.get("title", f.stem), version=int(head.get("version", "1") or 1),
                                          status=head.get("status", ""), approved_by=head.get("approved_by", ""), date=head.get("date", ""), text=body.strip()))
        connectors = []
        for place in (c.store.root / "connectors.json", c.config.dir / "connectors.json" if c.config.dir else None):
            if place and place.is_file():
                try:
                    connectors = [RuleConnector(**{k: str(v) for k, v in item.items() if not k.startswith("$")}) for item in json.loads(place.read_text(encoding="utf-8")).get("connectors", [])]
                except (OSError, ValueError, TypeError):
                    connectors = []
                break
        return RulesOut(stages=stages, skills=skills, modules=modules, connectors=connectors)

    @app.get("/api/stages", response_model=list[StageOut])
    def stages(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        out = []
        for folder in c.store.stages():
            st = c.config.stage(folder)
            cards = [views.card(c.config, reading.load(c.store, c.config, cid), who, c.lang) for cid in c.store.cases(folder)]
            out.append(StageOut(folder=folder, key=st.key if st else "", word=c.config.word("stages", folder, c.lang, folder),
                                station=c.config.word("stations", st.key, c.lang, "") if st and st.key else "", cases=cards))
        return out

    # ------------------------------------------------------------ writing: every write is a step
    def _answer(result: StepResult) -> JSONResponse:
        return JSONResponse(status_code=200 if result.ok else 409, content=result.model_dump(by_alias=True))

    @app.post("/api/cases/{case_id}/steps", response_model=StepResult)
    def post_step(case_id: str, body: StepRequest, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        return _answer(stepping.step(c.store, c.config, case_id, body, who))

    @app.post("/api/cases/{case_id}/entries", response_model=StepResult)
    def post_entry(case_id: str, body: EntryIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        if body.kind not in ("note", "answer", "done"):
            raise HTTPException(422, "kind must be note, answer or done")
        payload = {"text": body.text, "resolves": body.resolves or "", "for": body.for_ or "", "title": body.title or ""}
        return _answer(stepping.step(c.store, c.config, case_id, StepRequest(action=body.kind, step_id=body.step_id, payload=payload), who))

    @app.post("/api/cases/{case_id}/runs", response_model=StepResult)
    def post_run(case_id: str, body: RunIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        return _answer(stepping.step(c.store, c.config, case_id, StepRequest(action="ask", step_id=body.request_id, payload={"skill": body.skill, "text": body.note}), who))

    @app.post("/api/cases/{case_id}/assets", response_model=AssetOut)
    async def post_asset(case_id: str, slot: str = Form(...), step_id: str = Form(...), file: UploadFile = File(...), c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        data = await file.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"larger than {settings.max_upload_mb} MB")
        prior = stepping.read_journal(c.store, step_id)
        if prior is not None:
            return AssetOut(name=str(prior.payload.get("files", [""])[0]), slot=slot, step=stepping.step(c.store, c.config, case_id, StepRequest(action="deliver", step_id=step_id), who))
        try:
            name = assets.put(c.store, c.config, case_id, slot, data, file.filename or "")
        except StoreError as exc:
            raise HTTPException(409, str(exc))
        return AssetOut(name=name, slot=slot, step=stepping.step(c.store, c.config, case_id, StepRequest(action="deliver", step_id=step_id, payload={"files": [name], "title": ""}), who))

    @app.post("/api/cases/{case_id}/samples", response_model=AssetOut)
    def post_sample(case_id: str, body: SampleIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """The demo's 'put the sample invoice in': a bundled file lands in the slot as a delivered version."""
        samples_dir, samples = samples_of(c)
        if not settings.demo or not samples_dir or body.slot not in samples:
            raise HTTPException(404, "no sample for that slot")
        prior = stepping.read_journal(c.store, body.step_id)
        if prior is not None:
            return AssetOut(name=str(prior.payload.get("files", [""])[0]), slot=body.slot, step=stepping.step(c.store, c.config, case_id, StepRequest(action="deliver", step_id=body.step_id), who))
        try:
            name = assets.put(c.store, c.config, case_id, body.slot, samples_dir / body.slot, body.slot)
        except StoreError as exc:
            raise HTTPException(409, str(exc))
        return AssetOut(name=name, slot=body.slot, step=stepping.step(c.store, c.config, case_id, StepRequest(action="deliver", step_id=body.step_id, payload={"files": [name]}), who))

    # ------------------------------------------------------------ the surface
    if settings.web_dist and settings.web_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=settings.web_dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            candidate = settings.web_dist / path
            if path and ".." not in path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(settings.web_dist / "index.html")

    return app


def app_from_env() -> FastAPI:
    """`uvicorn casefile.api.app:app_from_env --factory`.

    One pipeline: CASEFILE_ROOT, CASEFILE_CONFIG. The demo: CASEFILE_DEMO_WORLDS=<dir with claims/, pressroom/ and egutachten/> (built by
    `python -m casefile.demo.worlds <dir>`), CASEFILE_SESSIONS=<dir>. Both: CASEFILE_WEB, CASEFILE_SECRET, CASEFILE_LANG.
    """
    here = Path(__file__).resolve().parents[2]
    web = Path(os.environ["CASEFILE_WEB"]) if os.environ.get("CASEFILE_WEB") else (here / "web" / "dist")
    secret = os.environ.get("CASEFILE_SECRET") or secrets.token_hex(16)
    if os.environ.get("CASEFILE_DEMO_WORLDS"):
        worlds_dir = Path(os.environ["CASEFILE_DEMO_WORLDS"]).expanduser()
        return create_app(Settings(secret=secret, web_dist=web, demo=True, samples_dir=here / "casefile" / "demo" / "samples",
                                   replies_dir=here / "casefile" / "demo" / "replies",
                                   worlds={"claims": World(config_dir=here / "config" / "claims-demo", template=worlds_dir / "claims", person="du", lang="de"),
                                           "pressroom": World(config_dir=here / "config" / "pressroom", template=worlds_dir / "pressroom", person="chris", lang="en"),
                                           "egutachten": World(config_dir=here / "config" / "egutachten", template=worlds_dir / "egutachten", person="du", lang="de")},
                                   default_world=os.environ.get("CASEFILE_DEFAULT_WORLD", "claims"),
                                   sessions_dir=Path(os.environ.get("CASEFILE_SESSIONS") or worlds_dir / "sessions"),
                                   open_identity=True))
    return create_app(Settings(root=Path(os.environ["CASEFILE_ROOT"]).expanduser(),
                               config_dir=Path(os.environ.get("CASEFILE_CONFIG") or here / "config" / "pressroom"),
                               lang=os.environ.get("CASEFILE_LANG"),
                               open_identity=os.environ.get("CASEFILE_OPEN_IDENTITY", "1") == "1",
                               secret=secret, web_dist=web,
                               demo=os.environ.get("CASEFILE_DEMO", "0") == "1",
                               samples_dir=here / "casefile" / "demo" / "samples", replies_dir=here / "casefile" / "demo" / "replies"))
