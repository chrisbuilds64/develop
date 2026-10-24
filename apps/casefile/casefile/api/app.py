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
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

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
LANG_COOKIE = "cf_lang"
WORLDS_COOKIE = "cf_worlds"       # the visitor's sandbox per world, so a switch returns to where they were           # the viewer's language, when it differs from the world's; plain, not secret


@dataclass
class World:
    config_dir: Path
    template: Path                               # a built pipeline root to copy per visitor
    person: str                                  # the visitor's identity in this world
    lang: str | None = None


@dataclass
class Settings:
    root: Path | None = None                     # one pipeline: the root
    write_root: Path | None = None               # one pipeline: where writes go when that differs (a WebDAV mount of the same tree)
    config_dir: Path | None = None               # one pipeline: config/<domain>
    lang: str | None = None
    open_identity: bool = True                   # POST /api/session {person} without a password (development, demo)
    identity: Callable[[Request], str | None] | None = None   # who is here, decided outside (the cockpit's login); then the own cookie is never read
    label: str | None = None                     # what the surface calls this workspace, when it differs from the domain's product name
    stage: str | None = None                     # "entw", "test": a stripe and a badge on every page of the surface; nothing for production
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
    world: str | None = None                                # switch to this world (the visitor's sandbox there is kept)
    fresh: bool = False                                     # a new sandbox for that world (start over)


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
    open_identity: bool = True                              # false: who you are was decided outside; no person picker
    identity: str | None = None                             # the outside identity, even when it matches nobody in people.json


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
        store = FsStore(settings.root, settings.write_root)
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
        if settings.identity is not None:
            outside = settings.identity(request)
            p = config.person(outside) if outside else None
            return p.id if p else None
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

    def _read_worlds(request: Request) -> dict[str, str]:
        """world → sandbox id, from the signed cookie; only sandboxes that still exist."""
        raw = request.cookies.get(WORLDS_COOKIE, "")
        if "." not in raw:
            return {}
        body, sig = raw.rsplit(".", 1)
        if not hmac.compare_digest(sig, _sign(settings.secret, body)):
            return {}
        out = {}
        for pair in body.split(","):
            if ":" in pair:
                w, sid = pair.split(":", 1)
                if w in settings.worlds and (settings.sessions_dir / sid).is_dir():
                    out[w] = sid
        return out

    def _set_worlds(response: Response, mapping: dict[str, str]) -> None:
        body = ",".join(f"{w}:{sid}" for w, sid in mapping.items())
        response.set_cookie(WORLDS_COOKIE, f"{body}.{_sign(settings.secret, body)}", httponly=True, samesite="lax", max_age=settings.session_hours * 3600)

    def _handover(request: Request, response: Response, c: Ctx, case_id: str, spec: dict, step_id: str) -> None:
        """Demo stand-in for a connector between two worlds (the GDV Schadennetz in the real thing): after the step, the
        case's files travel to the visitor's sandbox of the partner world. Two modes: `create` opens a new case there (a
        claim orders an assessment); `match` finds the case waiting for them (the e-report returns to its claim) and takes
        the partner's step. A failed hand-over is logged; the visitor's own step stands."""
        try:
            world = str(spec.get("world", ""))
            if world not in settings.worlds or not c.world:
                return
            mapping = _read_worlds(request)
            if c.session:
                mapping[c.world] = c.session
            target = _session_ctx(mapping[world]) if world in mapping else None
            if target is None:
                target = _new_session(world)
                mapping[world] = target.session
            _set_worlds(response, mapping)
            src_case = reading.load(c.store, c.config, case_id)
            src_dir = c.store.case_dir(case_id)
            rename = spec.get("rename", {})

            def newest(patterns):
                base_of = {}
                for pattern in patterns:
                    for h in sorted(src_dir.glob(pattern)):
                        base, v = reading.split_version(h.name)
                        if base not in base_of or v > base_of[base][1]:
                            base_of[base] = (h, v)
                return [(rename.get(base, base), h) for base, (h, _) in base_of.items()]

            create = spec.get("create")
            if create:
                number = str(src_case.meta.get("number") or case_id)
                ref = str(create.get("external_prefix", "")) + number.replace("2026-", "2026-0")
                slug = "-".join(case_id.split("-")[3:]) or "auftrag"
                new_id = f"{create.get('label', 'KH')}-{number}-{slug}"
                stage = str(create.get("stage"))
                d = target.store.root / stage / new_id
                if d.exists():
                    return
                d.mkdir(parents=True)
                meta = {"configVersion": "1", "fictional": True, "label": create.get("label", "KH"), "number": number, "title": str(src_case.meta.get("title") or case_id),
                        "created": _now()[:10], "external_id": ref, "subtitle": str(src_case.meta.get("subtitle") or ""), "client": str(create.get("client", "")),
                        "schaden_nr": str(src_case.meta.get("external_id") or case_id), "origin": f"{c.world}/{case_id}"}
                (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                for name, h in newest(spec.get("files", [])):
                    shutil.copy(h, d / name)
                # the source case remembers which order it placed
                src_meta = {**src_case.meta, str(spec.get("match", "gutachten_auftrag")): ref}
                c.store.write_atomic(f"{src_case.stage}/{case_id}/meta.json", json.dumps(src_meta, ensure_ascii=False, indent=2) + "\n")
                note = str(spec.get("note", "")).replace("{ref}", ref).replace("{claim}", meta["schaden_nr"])
                stepping.step(target.store, target.config, new_id, StepRequest(action="note", step_id=f"{step_id}-handover", payload={"title": str(create.get("title", "")).replace("{claim}", meta["schaden_nr"]), "text": note, "files": [n for n, _ in newest(spec.get("files", []))]}), str(spec.get("by", "")))
                return
            key = str(spec.get("match", "external_id"))
            ref = str(src_case.meta.get("external_id") or case_id)
            partner = next((k for k in reading.load_all(target.store, target.config) if str(k.meta.get(key, "")) == ref), None)
            if partner is None:
                return
            written = [assets.put(target.store, target.config, partner.id, name, h, h.name) for name, h in newest(spec.get("files", []))]
            payload = {"files": written, "note": str(spec.get("note", ""))}
            stepping.step(target.store, target.config, partner.id, StepRequest(action=str(spec.get("action", "deliver")), step_id=f"{step_id}-handover", payload=payload), str(spec.get("by", "")))
        except Exception as exc:        # noqa: BLE001 — a failed hand-over must never break the visitor's own step
            try:
                (settings.sessions_dir / "handover-errors.log").open("a", encoding="utf-8").write(f"{_now()} {c.world}/{case_id} {step_id}: {exc!r}\n")
            except OSError:
                pass

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
        _set_worlds(response, {**_read_worlds(request), c.world: c.session})
        _set_person(response, settings.worlds[c.world].person)
        request.state.fresh_person = settings.worlds[c.world].person
        return c

    def viewer(request: Request, c: Ctx = Depends(ctx)) -> str:
        who = getattr(request.state, "fresh_person", None) or _who(request, c.config)
        if not who:
            raise HTTPException(401, "not signed in")
        return who

    def product(c: Ctx) -> str:
        if settings.label:
            return settings.label
        v = c.config.vocabulary.get(c.lang) or c.config.vocabulary.get("en") or {}
        return str(v.get("product") or c.config.name)

    def me_out(c: Ctx, person_id: str | None, request: Request | None = None) -> MeOut:
        p = c.config.person(person_id) if person_id else None
        outside = settings.identity(request) if (settings.identity is not None and request is not None) else None
        return MeOut(person=p.id if p else None, name=p.name if p else None, roles=p.roles if p else [], lang=c.lang, product=product(c),
                     demo=settings.demo, world=c.world, worlds=list(settings.worlds),
                     open_identity=settings.open_identity and settings.identity is None, identity=outside)

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
        if not settings.open_identity or settings.identity is not None:
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
        mapping = _read_worlds(request)
        current = None
        raw = request.cookies.get(DEMO_COOKIE, "")
        if "." in raw:
            sid, sig = raw.rsplit(".", 1)
            if hmac.compare_digest(sig, _sign(settings.secret, sid)):
                current = _session_ctx(sid)
        world = (body.world if body and body.world else None) or (current.world if current else None) or settings.default_world
        if world not in settings.worlds:
            raise HTTPException(404, f"no world '{world}'")
        fresh = bool(body and body.fresh) or not (body and body.world)      # "start over" is fresh; a switch keeps the sandbox
        c = None if fresh else (_session_ctx(mapping[world]) if world in mapping else None)
        if c is None:
            c = _new_session(world)
        mapping[world] = c.session
        _set_worlds(response, mapping)
        _set_session(response, c.session)
        _set_person(response, settings.worlds[world].person)
        return me_out(c, settings.worlds[world].person)

    @app.get("/api/me", response_model=MeOut)
    def me(request: Request, c: Ctx = Depends(ctx)):
        return me_out(c, getattr(request.state, "fresh_person", None) or _who(request, c.config), request)

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
    def post_step(case_id: str, body: StepRequest, request: Request, response: Response, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        result = stepping.step(c.store, c.config, case_id, body, who)
        if result.ok and not result.replayed and settings.worlds:
            action = next((a for st in c.config.stages for a in st.actions if a.id == body.action and a.handover), None)
            if action:
                _handover(request, response, c, case_id, action.handover, body.step_id)
        answer = _answer(result)
        for k, v in response.headers.items():        # cookies the hand-over set travel with the JSON answer
            if k.lower() == "set-cookie":
                answer.headers.append(k, v)
        return answer

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
        index_html = (settings.web_dist / "index.html").read_text(encoding="utf-8")
        _ROOTED = re.compile(r'((?:src|href)=")/(?!/)')

        STAGE_COLOR = {"entw": "#c62828", "test": "#1d4ed8"}

        def index_for(prefix: str) -> str:
            """One build, served under any prefix: rooted asset paths get the prefix, and the surface learns its base
            from a meta tag (api.ts reads it before it falls back to the build-time BASE_URL). A stage other than
            production gets a stripe along the top and a badge, injected here so the build stays one build."""
            html = _ROOTED.sub(lambda m: m.group(1) + prefix + "/", index_html) if prefix else index_html
            html = html.replace("<head>", f'<head>\n    <meta name="cf-base" content="{prefix}" />', 1)
            stage = (settings.stage or "").lower()
            if stage and stage != "prod":
                color = STAGE_COLOR.get(stage, "#1d4ed8")
                mark = (f'<style>.cf-stage{{position:fixed;top:0;left:0;right:0;height:4px;background:{color};z-index:9999}}'
                        f'.cf-stage-badge{{position:fixed;top:8px;right:12px;z-index:9999;font:700 11px/1 system-ui,sans-serif;letter-spacing:.08em;'
                        f'color:#fff;background:{color};padding:4px 8px;border-radius:999px;pointer-events:none}}</style>\n'
                        f'    <meta name="cf-stage" content="{stage}" />')
                html = html.replace("</head>", mark + "\n  </head>", 1)
                html = html.replace("<body>", f'<body>\n    <div class="cf-stage" aria-hidden="true"></div><div class="cf-stage-badge">{stage.upper()}</div>', 1)
            return html

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str, request: Request):
            candidate = settings.web_dist / path
            if path and ".." not in path and candidate.is_file():
                return FileResponse(candidate)
            prefix = str(request.scope.get("root_path", "") or "").rstrip("/")
            return Response(index_for(prefix), media_type="text/html")

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
