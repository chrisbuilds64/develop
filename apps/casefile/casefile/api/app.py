"""The core's API (Bauplan §4). JSON in, JSON out; the surface is static files served beside it (ADR-014).

Every request leaves one audit line in `<root>/_audit/api.jsonl`. Identity is a signed cookie naming a
person from people.json; how it is obtained depends on the deployment (open in development and in the
demo sandbox, a login later). The core recovers half-done steps on start and records manual moves on read.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
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


@dataclass
class Settings:
    root: Path                                   # the pipeline root
    config_dir: Path                             # config/<domain>
    lang: str | None = None
    open_identity: bool = True                   # POST /api/session {person} without a password (development, demo)
    secret: str = field(default_factory=lambda: secrets.token_hex(16))
    web_dist: Path | None = None                 # the built surface, served at /
    max_upload_mb: int = 10
    recover_on_start: bool = True
    demo: bool = False                           # the public demo: samples offered, prepared replies played back
    samples_dir: Path | None = None              # bundled sample files by slot file name (demo)
    replies_dir: Path | None = None              # prepared replies by skill (demo)


class SessionIn(BaseModel):
    person: str


class EntryIn(BaseModel):
    kind: str = "note"                           # note | answer | done
    step_id: str
    text: str = ""
    for_: str | None = Field(default=None, alias="for")
    resolves: str | None = None
    title: str | None = None

    model_config = {"populate_by_name": True}


class RunIn(BaseModel):
    skill: str = "interpret"
    note: str = ""
    request_id: str


class MeOut(BaseModel):
    person: str | None
    name: str | None
    roles: list[str] = Field(default_factory=list)
    lang: str
    product: str


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
    cases: list[views.CaseCard]


class AssetOut(BaseModel):
    name: str
    slot: str
    step: StepResult


class SampleIn(BaseModel):
    slot: str
    step_id: str


def _sign(secret: str, value: str) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:32]


def create_app(settings: Settings) -> FastAPI:
    store = FsStore(settings.root)
    config = DomainConfig.load(settings.config_dir, settings.root)
    lang = settings.lang or config.lang
    app = FastAPI(title="casefile", version=__version__, description=__doc__)
    app.state.settings, app.state.store, app.state.config = settings, store, config

    if settings.recover_on_start:
        stepping.recover(store, config)
    if settings.demo and settings.replies_dir:
        from ..demo.replay import ReplayRunner
        app.state.replay = ReplayRunner([(store, config)], settings.replies_dir).start()
    samples = sorted(p.name for p in settings.samples_dir.iterdir()) if settings.samples_dir and settings.samples_dir.is_dir() else []

    # ------------------------------------------------------------ audit, one line per request
    @app.middleware("http")
    async def audit(request: Request, call_next):
        t0 = time.perf_counter()
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            line = {"at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "who": _who(request) or "-",
                    "method": request.method, "path": request.url.path, "status": response.status_code,
                    "ms": round((time.perf_counter() - t0) * 1000)}
            store.append("_audit/api.jsonl", json.dumps(line, ensure_ascii=False) + "\n")
        return response

    # ------------------------------------------------------------ identity
    def _who(request: Request) -> str | None:
        raw = request.cookies.get(COOKIE, "")
        if "." not in raw:
            return None
        person, sig = raw.rsplit(".", 1)
        if hmac.compare_digest(sig, _sign(settings.secret, person)) and config.person(person):
            return config.person(person).id
        return None

    def viewer(request: Request) -> str:
        who = _who(request)
        if not who:
            raise HTTPException(401, "not signed in")
        return who

    def file_url(case: Case, name: str) -> str:
        return f"/api/cases/{case.id}/files/{name}"

    # ------------------------------------------------------------ session
    @app.post("/api/session", response_model=MeOut)
    def session(body: SessionIn, response: Response):
        if not settings.open_identity:
            raise HTTPException(403, "this deployment does not accept an open identity")
        p = config.person(body.person)
        if p is None or p.kind != "human":
            raise HTTPException(404, f"'{body.person}' is not a person here")
        response.set_cookie(COOKIE, f"{p.id}.{_sign(settings.secret, p.id)}", httponly=True, samesite="lax", max_age=30 * 24 * 3600)
        return MeOut(person=p.id, name=p.name, roles=p.roles, lang=lang, product=_product())

    @app.delete("/api/session")
    def end_session(response: Response):
        response.delete_cookie(COOKIE)
        return {"ok": True}

    @app.get("/api/me", response_model=MeOut)
    def me(request: Request):
        who = _who(request)
        p = config.person(who) if who else None
        return MeOut(person=p.id if p else None, name=p.name if p else None, roles=p.roles if p else [], lang=lang, product=_product())

    def _product() -> str:
        v = config.vocabulary.get(lang) or config.vocabulary.get("en") or {}
        return str(v.get("product") or config.name)

    # ------------------------------------------------------------ reading
    @app.get("/api/config", response_model=views.ConfigView)
    def get_config():
        v = views.config_view(config, lang)
        v.theme = {**v.theme, "demo": settings.demo, "samples": samples if settings.demo else []}
        return v

    @app.post("/api/cases/{case_id}/samples", response_model=AssetOut)
    def post_sample(case_id: str, body: SampleIn, who: str = Depends(viewer)):
        """The demo's 'put the sample invoice in': a bundled file lands in the slot as a delivered version."""
        if not settings.demo or not settings.samples_dir or body.slot not in samples:
            raise HTTPException(404, "no sample for that slot")
        prior = stepping.read_journal(store, body.step_id)
        if prior is not None:
            return AssetOut(name=str(prior.payload.get("files", [""])[0]), slot=body.slot, step=stepping.step(store, config, case_id, StepRequest(action="deliver", step_id=body.step_id), who))
        try:
            name = assets.put(store, config, case_id, body.slot, settings.samples_dir / body.slot, body.slot)
        except StoreError as exc:
            raise HTTPException(409, str(exc))
        result = stepping.step(store, config, case_id, StepRequest(action="deliver", step_id=body.step_id, payload={"files": [name]}), who)
        return AssetOut(name=name, slot=body.slot, step=result)

    @app.get("/api/me/turns", response_model=list[TurnOut])
    def my_turns(who: str = Depends(viewer)):
        stepping.detect(store, config)
        all_cases = reading.load_all(store, config)
        return [TurnOut(case=views.card(config, c, who, lang), turn=t) for c, t in whose.turns_for(who, all_cases, config, lang)]

    @app.get("/api/cases", response_model=list[GroupOut])
    def list_cases(group: str | None = None, who: str = Depends(viewer)):
        stepping.detect(store, config)
        cards = [views.card(config, c, who, lang) for c in reading.load_all(store, config)]
        order = ["you", "claude", "others", "date", "planned", "out", "ideas", "archive"]
        out = []
        for g in order:
            if group and g != group:
                continue
            mine = [c for c in cards if c.group == g]
            if g == "out":
                mine.sort(key=lambda c: c.date, reverse=True)
            else:
                mine.sort(key=lambda c: c.since)
            out.append(GroupOut(key=g, word=config.word("groups", g, lang, g), cases=mine))
        return out

    @app.get("/api/cases/{case_id}", response_model=views.CaseView)
    def get_case(case_id: str, who: str = Depends(viewer)):
        try:
            case = reading.load(store, config, case_id)
        except (KeyError, StoreError) as exc:
            raise HTTPException(404, str(exc) or case_id)
        return views.view(config, case, who, lang, file_url)

    @app.get("/api/cases/{case_id}/files/{name}")
    def get_file(case_id: str, name: str, who: str = Depends(viewer)):
        if "/" in name or name.startswith("."):
            raise HTTPException(404, name)
        try:
            p = store.case_dir(case_id) / name
        except StoreError:
            raise HTTPException(404, case_id)
        if not p.is_file():
            raise HTTPException(404, name)
        return FileResponse(p)

    @app.get("/api/stages", response_model=list[StageOut])
    def stages(who: str = Depends(viewer)):
        out = []
        for folder in store.stages():
            st = config.stage(folder)
            cards = [views.card(config, reading.load(store, config, cid), who, lang) for cid in store.cases(folder)]
            out.append(StageOut(folder=folder, key=st.key if st else "", word=config.word("stages", folder, lang, folder), cases=cards))
        return out

    # ------------------------------------------------------------ writing: every write is a step
    @app.post("/api/cases/{case_id}/steps", response_model=StepResult)
    def post_step(case_id: str, body: StepRequest, who: str = Depends(viewer)):
        result = stepping.step(store, config, case_id, body, who)
        return JSONResponse(status_code=200 if result.ok else 409, content=result.model_dump(by_alias=True))

    @app.post("/api/cases/{case_id}/entries", response_model=StepResult)
    def post_entry(case_id: str, body: EntryIn, who: str = Depends(viewer)):
        if body.kind not in ("note", "answer", "done"):
            raise HTTPException(422, "kind must be note, answer or done")
        payload = {"text": body.text, "resolves": body.resolves or "", "for": body.for_ or "", "title": body.title or ""}
        result = stepping.step(store, config, case_id, StepRequest(action=body.kind, step_id=body.step_id, payload=payload), who)
        return JSONResponse(status_code=200 if result.ok else 409, content=result.model_dump(by_alias=True))

    @app.post("/api/cases/{case_id}/runs", response_model=StepResult)
    def post_run(case_id: str, body: RunIn, who: str = Depends(viewer)):
        result = stepping.step(store, config, case_id, StepRequest(action="ask", step_id=body.request_id, payload={"skill": body.skill, "text": body.note}), who)
        return JSONResponse(status_code=200 if result.ok else 409, content=result.model_dump(by_alias=True))

    @app.post("/api/cases/{case_id}/assets", response_model=AssetOut)
    async def post_asset(case_id: str, slot: str = Form(...), step_id: str = Form(...), file: UploadFile = File(...), who: str = Depends(viewer)):
        data = await file.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"larger than {settings.max_upload_mb} MB")
        prior = stepping.read_journal(store, step_id)
        if prior is not None:                                   # the same upload twice: the first outcome
            return AssetOut(name=str(prior.payload.get("files", [""])[0]), slot=slot, step=stepping.step(store, config, case_id, StepRequest(action="deliver", step_id=step_id), who))
        try:
            name = assets.put(store, config, case_id, slot, data, file.filename or "")
        except StoreError as exc:
            raise HTTPException(409, str(exc))
        result = stepping.step(store, config, case_id, StepRequest(action="deliver", step_id=step_id, payload={"files": [name], "title": ""}), who)
        return AssetOut(name=name, slot=slot, step=result)

    # ------------------------------------------------------------ the surface
    if settings.web_dist and settings.web_dist.is_dir():
        app.mount("/assets", StaticFiles(directory=settings.web_dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            candidate = settings.web_dist / path
            if path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(settings.web_dist / "index.html")

    return app


def app_from_env() -> FastAPI:
    """`uvicorn casefile.api.app:app_from_env --factory` with CASEFILE_ROOT, CASEFILE_CONFIG, CASEFILE_WEB, CASEFILE_SECRET."""
    here = Path(__file__).resolve().parents[2]
    return create_app(Settings(root=Path(os.environ["CASEFILE_ROOT"]).expanduser(),
                               config_dir=Path(os.environ.get("CASEFILE_CONFIG") or here / "config" / "pressroom"),
                               lang=os.environ.get("CASEFILE_LANG"),
                               open_identity=os.environ.get("CASEFILE_OPEN_IDENTITY", "1") == "1",
                               secret=os.environ.get("CASEFILE_SECRET") or secrets.token_hex(16),
                               web_dist=Path(os.environ["CASEFILE_WEB"]) if os.environ.get("CASEFILE_WEB") else (here / "web" / "dist"),
                               demo=os.environ.get("CASEFILE_DEMO", "0") == "1",
                               samples_dir=here / "casefile" / "demo" / "samples", replies_dir=here / "casefile" / "demo" / "replies"))
