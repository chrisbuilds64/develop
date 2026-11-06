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
from typing import Callable, Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .. import __version__
from ..config import DomainConfig
from ..domain import assets, cases as reading, step as stepping
from ..domain import runs as runs_
from ..domain import seen as reads
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
    targets: dict[str, str] = field(default_factory=dict)   # hand-off target → world: the inbox opens cases in the visitor's other sandboxes


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
    shell: str | None = None                     # where the shell that mounted this app lives ("/entw/"): the menu offers the way back
    peers: Callable[[Request | None], list[dict]] | None = None   # inside a shell: every workspace this person may open ({id, name, url, color, icon, current})
    plugins: list[dict] | None = None             # inside a shell: the shell's plugins ({id, name, version, text}); without one, the demo's copy
    secret: str = field(default_factory=lambda: secrets.token_hex(16))
    web_dist: Path | None = None                 # the built surface, served at /
    max_upload_mb: int = 10
    recover_on_start: bool = True
    demo: bool = False                           # samples offered, prepared replies played back
    template: Path | None = None                 # a sample workspace's world: POST /api/demo/reset puts the tree back to it
    samples_dir: Path | None = None
    replies_dir: Path | None = None
    worlds: dict[str, World] = field(default_factory=dict)      # the public demo: name → world
    default_world: str = "claims"
    sessions_dir: Path | None = None
    session_hours: int = 24
    session_cap: int = 500
    rate_per_minute: int = 1200                  # requests per IP and minute — a room shares one Wi-Fi address
    sessions_per_minute: int = 60                # new sandboxes per IP and minute


def in_lang(head: dict, body: str, lang: str) -> tuple[dict, str]:
    """A rule, template or hint in the viewer's language (request 8): header keys `title_en`, `source_en` … win over
    `title`, `source`; a body after a line `<!-- en -->` wins over the original before it. Without them, the original."""
    out = {**head}
    for k, v in head.items():
        if k.endswith(f"_{lang}") and v:
            out[k[: -len(lang) - 1]] = v
    parts = re.split(r"\n?<!--\s*([a-z]{2})\s*-->\n?", body or "")
    original, versions = parts[0], dict(zip(parts[1::2], parts[2::2]))
    return out, (versions.get(lang) or original).strip()


class SessionIn(BaseModel):
    person: str


class LangIn(BaseModel):
    lang: str


class DemoSessionIn(BaseModel):
    world: str | None = None                                # switch to this world (the visitor's sandbox there is kept)
    fresh: bool = False                                     # a new sandbox for that world (start over)


class SeenIn(BaseModel):
    unread: bool = False                         # false: the viewer has read the case now; true: mark it as new again


class SeenOut(BaseModel):
    case: str
    unread: bool


class EntryIn(BaseModel):
    kind: str = "note"                           # note | answer | done
    step_id: str
    text: str = ""
    for_: str | None = Field(default=None, alias="for")
    resolves: str | None = None
    title: str | None = None

    model_config = {"populate_by_name": True}


class TranslateIn(BaseModel):
    file: str                                    # the original in the case: mail.md, meldung.md …
    lang: str | None = None                      # the language wanted; the viewer's when empty
    request_id: str


class TranslateOut(BaseModel):
    original: str
    lang: str
    name: str                                    # the translation's file beside the original
    ready: bool                                  # true: it is there; false: a helper is writing it
    run: str | None = None


class RunIn(BaseModel):
    skill: str = "ask"
    note: str = ""
    request_id: str


class SampleIn(BaseModel):
    slot: str
    step_id: str
    source: str | None = None        # a sample under another name: `vorort-hinten.jpg` into the next photo of a series


class OnsiteIn(BaseModel):
    """The assessor's state at the car: which view each photo shows, what they ticked or answered of the AI's hints."""
    photos: dict[str, str] = {}
    hints: dict[str, dict] = {}


class PlaceOut(BaseModel):
    """A workspace the person can be in, for the menu: its name, its colour and glyph (theme.app), whether it is this one."""
    id: str
    name: str
    color: str = ""
    icon: str = ""
    current: bool = False
    url: str = ""                                           # inside a shell: where this workspace lives; empty for this one and for demo worlds
    count: int = 0                                          # cases waiting for this person there (the demo knows it for every world)


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
    shell: str | None = None                                # the shell's URL, when this app runs inside one
    places: list[PlaceOut] = []                             # this workspace and, in the demo, the other worlds
    waiting_rules: int = 0                                  # rule changes this person may accept, waiting (the dot on Rulebook)
    waiting_signals: int = 0                                # hints still to check (the dot on Flagged)
    team: str | None = None                                 # where the AI team lives: "cockpit" (the shell's, the person's own), "demo" (the visitor's), none


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
    areas: list[str] = []                        # the labels it applies to; empty = all (ADR-026)
    draft: int | None = None                     # the version of an open draft, waiting for a second person
    versions: int = 1                            # how many versions its history holds
    in_force: bool = True                        # false: only proposed so far, nothing of it holds yet
    use: str = ""                                # a letter template: where it is used ("every letter")
    source: str = ""                             # where it came from ("from a talk with …"), as the proposal says
    draft_text: str = ""                         # the open draft, for the person who decides on it
    draft_title: str = ""
    draft_areas: list[str] = []
    draft_by: str = ""
    draft_date: str = ""
    draft_note: str = ""


class ModuleVersion(BaseModel):
    version: int
    status: str
    title: str
    text: str
    areas: list[str] = []
    date: str = ""
    approved_by: str = ""
    drafted_by: str = ""
    note: str = ""
    source: str = ""
    reason: str = ""                             # why it was rejected or retired


class ModuleHistory(BaseModel):
    id: str
    in_force: ModuleVersion | None = None
    draft: ModuleVersion | None = None
    versions: list[ModuleVersion]
    may_edit: bool = False                       # the viewer writes drafts and retires
    may_approve: bool = False                    # the viewer may bring the open draft into force (not its author)


class DraftIn(BaseModel):
    text: str
    title: str = ""
    kind: str = ""                               # a new module: Regel, Baustein …
    areas: list[str] | None = None               # None keeps the areas it had
    note: str = ""                               # what changed, for the history


class RetireIn(BaseModel):
    note: str


class RuleConnector(BaseModel):
    id: str
    name: str
    standard: str = ""
    carries: str = ""
    direction: str = ""
    note: str = ""


class SetupItem(BaseModel):
    id: str
    name: str
    side: str = ""                                          # the short word on the right: a version, a direction, who holds it, how many
    text: str = ""                                          # what opens below: what it is, what it carries
    items: list[str] = []                                   # the parts, where it has some (a schema's documents)


class SetupOut(BaseModel):
    """Setup (design hand-back, 2026-11-06): what this workspace is built from, read from its configuration."""
    plugins: list[SetupItem]
    sources: list[SetupItem]
    roles: list[SetupItem]
    schemas: list[SetupItem]


class SignalCase(BaseModel):
    id: str
    title: str
    external_id: str = ""
    stage_word: str = ""
    color: str = ""                              # its label's colour (the value list `label`), for the chip


class SignalStatusIn(BaseModel):
    status: Literal["offen", "in_pruefung", "erledigt"]


class SignalOut(BaseModel):
    """A hint the pattern helper found across files: never a finding, always with its reasoning and the files it rests on."""
    id: str
    kind: str
    title: str
    status: str
    date: str
    cases: list[SignalCase]
    text: str
    decided_by: str = ""                         # who last moved it (looking into it, done, back to open)
    decided_at: str = ""


class MatrixRow(BaseModel):
    """One row of the rule matrix, in the viewer's words: when a mail is of this kind, this happens."""
    id: str
    kind: str
    word: str
    when: str = ""
    action: str
    action_word: str
    target: str = ""
    target_word: str = ""
    connected: bool = True
    approval: str = "human"


class RuleArea(BaseModel):
    """An area a rule can apply to: a case label with its word and colour (the value list `label`)."""
    key: str
    word: str
    color: str = ""


class RejectIn(BaseModel):
    reason: str


class RulesOut(BaseModel):
    """The rulebook: stages and gates, what each helper does and never does, the approved modules and rules with versions, the connectors."""
    stages: list[RuleStage]
    skills: list[RuleSkill]
    modules: list[RuleModule]
    connectors: list[RuleConnector] = []
    matrix: list[MatrixRow] = []
    may_edit: bool = False                       # the viewer may change rules and modules (an operator)
    may_decide: bool = False                     # the viewer may accept or reject a proposed change (an operator or approver)
    areas: list[RuleArea] = []                   # the areas rules can apply to; a rule without areas holds for the whole office
    me: str = ""                                 # the viewer's name, so the surface can say "you wrote this" (four eyes)


class AnswerIn(BaseModel):
    question: str
    text: str = ""
    marker: str = ""
    step_id: str


class AnchorIn(BaseModel):
    text: str


class FollowupIn(BaseModel):
    followup: str
    text: str = ""
    step_id: str


class ChapterIn(BaseModel):
    block: str
    step_id: str


class FinishIn(BaseModel):
    step_id: str


class DecideIn(BaseModel):
    line: str
    verdict: str
    text: str = ""
    step_id: str


class NewCaseIn(BaseModel):
    title: str
    label: str | None = None
    step_id: str
    values: dict[str, str] = Field(default_factory=dict)   # field → key, from the lists a new case asks for (lists.json `on_create`)


class ListsOut(BaseModel):
    may_edit: bool                                        # the viewer runs the place (role operator): may start lists and change entries
    lists: list[views.ListView]


class ListIn(BaseModel):
    id: str
    word: dict[str, str] = Field(default_factory=dict)    # {de, en}
    field: str | None = None                              # the meta key it fills; fixed once the list exists
    on_create: bool | None = None
    step_id: str


class ListEntryIn(BaseModel):
    key: str
    word: dict[str, str] = Field(default_factory=dict)
    color: str | None = None
    description: str | None = None
    status: str | None = None                             # planned | active | retired
    step_id: str


class ListChangeOut(BaseModel):
    ok: bool
    line: dict                                            # the log line in _lists/log.jsonl
    list: views.ListView


class RespondentOut(BaseModel):
    id: str
    name: str
    answered: int
    total: int
    done: bool
    me: bool = False


class InterviewOut(BaseModel):
    """What one respondent sees of a conversation: the pack, their own answers and follow-ups, and how far everyone is.
    Nobody sees another person's answers here; that is the outcome's business."""
    case: str
    title: str
    pack: dict
    me: str
    can_answer: bool
    anchor: str = ""
    answers: dict = Field(default_factory=dict)        # question → {text, marker, at}
    followup_answers: dict = Field(default_factory=dict)
    helper: dict = Field(default_factory=dict)         # the helper's file for me: followups, tensions, drafts
    helper_running: bool = False
    done: bool = False
    respondents: list[RespondentOut] = []
    sees_all: bool = False                             # moderation and decider see names and progress; a respondent sees only how many others
    others: int = 0
    others_done: int = 0


class OutcomeOut(BaseModel):
    """The outcome: the findings, the draft with each line's decision, and the compiled canon when there is one."""
    case: str
    title: str
    stage_word: str
    blocks: list[dict] = []                            # id, title, canon — the chapters, in order
    findings: dict = Field(default_factory=dict)
    lines: list[dict] = []                             # the draft's lines, each with its decision
    can_decide: bool = False
    open_lines: int = 0
    canon: str | None = None                           # the newest compiled canon file
    canon_url: str | None = None
    running: bool = False
    people: dict = Field(default_factory=dict)         # id → name
    subtitle: str = ""
    version: int = 0                                   # the compiled canon's version (1 = canon.md, 2 = canon.v2.md …)
    approved_by: str = ""                              # the decider's name, from the decisions
    approved_at: str = ""                              # the newest decision's time
    canon_map: dict = Field(default_factory=dict)      # basis, marke, areas — where this canon stands (canonical-hierarchy, depth)


class SealOut(BaseModel):
    case: str
    title: str
    label: str
    action: str                                        # the gate's word ("Kanon freigeben")
    at: str


class RhythmOut(BaseModel):
    """What this person moved, honestly counted from the step journals: today and the last seven days. No streak, nothing
    to lose — a rhythm to come back to."""
    today_steps: int = 0
    today_seals: list[SealOut] = []
    week_steps: int = 0
    week_seals: int = 0


class NewCaseOut(BaseModel):
    id: str
    stage: str


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
        """After the step, the action's hand-over (domain/handoff.py). Here only the target is found: in the cockpit the stage
        names it (targets.json, ADR-022); in the public demo it is the visitor's sandbox of the partner world. A failed hand-over
        stands in the case's thread for the person to see; the step itself stands."""
        from ..domain import handoff
        key = str(spec.get("target") or spec.get("world") or "")
        try:
            if key == "self":                       # a follow-up in the same workspace (an order that comes out of a decision): no target to connect
                tgt = handoff.Target(key="self", store=c.store, config=c.config, label=c.config.name)
            elif settings.worlds:
                if key not in settings.worlds or not c.world:
                    return
                mapping = _read_worlds(request)
                if c.session:
                    mapping[c.world] = c.session
                other = _session_ctx(mapping[key]) if key in mapping else None
                if other is None:
                    other = _new_session(key)
                    mapping[key] = other.session
                _set_worlds(response, mapping)
                tgt = handoff.Target(key=key, store=other.store, config=other.config, label=other.config.name)
            else:
                tgt = handoff.target(c.store, key)
            handoff.hand_over(c.store, c.config, case_id, tgt, spec, "", request_id=f"{step_id}-handover")
        except Exception as exc:        # noqa: BLE001 — a failed hand-over never undoes the step; it is said where the person looks
            try:
                stage = c.store.find(case_id)
                if stage:
                    stepping._append_entry(c.store, c.config, case_id, stage, {"author": c.config.name, "status": "open",
                                           "title": f"Übergabe an {key} nicht gelungen", "text": str(exc)})
            except Exception:           # noqa: BLE001
                pass

    def ctx(request: Request, response: Response) -> Ctx:
        """The store and configuration this request works on, in the viewer's language if they chose one the domain speaks."""
        c = _ctx(request, response)
        # inside the cockpit, the shell's language holds until the viewer picks one here
        lang = request.cookies.get(LANG_COOKIE, "") or (request.cookies.get("lang", "") if settings.shell else "")
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

    def place(world: str | None, cfg: DomainConfig, lang: str, current: bool) -> PlaceOut:
        v = cfg.vocabulary.get(lang) or cfg.vocabulary.get("en") or {}
        mark = cfg.theme.get("app") if isinstance(cfg.theme.get("app"), dict) else {}
        name = (settings.label if current and settings.label else None) or str(v.get("workspace") or v.get("product") or cfg.name)
        return PlaceOut(id=world or "here", name=name, color=str(mark.get("color") or ""), icon=str(mark.get("icon") or ""), current=current)

    template_counts: dict[str, int] = {}

    def turns_count(store: FsStore, config: DomainConfig, person: str | None, lang: str) -> int:
        if not person:
            return 0
        try:
            return len({case.id for case, _ in whose.turns_for(person, reading.load_all(store, config), config, lang)})
        except Exception:                    # noqa: BLE001 — a count in the rail never breaks the rail
            return 0

    def world_count(request: Request | None, name: str, lang: str) -> int:
        """In the demo: what waits for the visitor in a world, from their sandbox there, or from the world as it starts."""
        w = settings.worlds[name]
        sid = _read_worlds(request).get(name) if request is not None else None
        other = _session_ctx(sid) if sid else None
        if other is not None:
            return turns_count(other.store, other.config, w.person, lang)
        if name not in template_counts:
            template_counts[name] = turns_count(FsStore(w.template), world_configs[name], w.person, lang)
        return template_counts[name]

    def waiting(c: Ctx, person_id: str | None) -> tuple[int, int]:
        from ..domain import rulebook
        me = c.config.person(person_id) if person_id else None
        rules = 0
        if me and me.kind == "human" and set(me.roles) & {"operator", "approver"}:
            drafts = [rulebook.draft_of(c.store, mid) for mid in rulebook.current(c.store)] + list(rulebook.proposed(c.store).values())
            rules = sum(1 for d in drafts if d and d.get("drafted_by") != me.name)
        folder = c.store.root / "_signale"
        signals = sum(1 for f in folder.glob("*.md") if not re.search(r"^status:\s*(in_pruefung|erledigt)\s*$", f.read_text(encoding="utf-8"), re.M)) if folder.is_dir() else 0
        return rules, signals

    def me_out(c: Ctx, person_id: str | None, request: Request | None = None) -> MeOut:
        p = c.config.person(person_id) if person_id else None
        places = [place(name, world_configs[name], c.lang, name == c.world) for name in settings.worlds] if settings.worlds else [place(c.world, c.config, c.lang, True)]
        for pl in places:
            if settings.worlds and pl.id in settings.worlds:
                pl.count = turns_count(c.store, c.config, person_id, c.lang) if pl.current else world_count(request, pl.id, c.lang)
            elif pl.current:
                pl.count = turns_count(c.store, c.config, person_id, c.lang)
        wr, ws = waiting(c, person_id)
        if settings.peers is not None:
            # inside the cockpit: the person's other workspaces sit beside this one in the rail, in the cockpit's order
            peers = settings.peers(request)
            mine = places[0].model_copy(update={"id": next((str(p["id"]) for p in peers if p.get("current")), places[0].id)})
            places = [mine if p.get("current") else PlaceOut(id=str(p["id"]), name=str(p.get("name") or p["id"]), color=str(p.get("color") or ""),
                                                             icon=str(p.get("icon") or ""), url=str(p.get("url") or "")) for p in peers]
            if not any(p.current for p in places):
                places.insert(0, mine)
        outside = settings.identity(request) if (settings.identity is not None and request is not None) else None
        return MeOut(person=p.id if p else None, name=p.name_in(c.lang) if p else None, roles=p.roles if p else [], lang=c.lang, product=product(c),
                     demo=settings.demo, world=c.world, worlds=list(settings.worlds),
                     open_identity=settings.open_identity and settings.identity is None, identity=outside, shell=settings.shell, places=places,
                     waiting_rules=wr, waiting_signals=ws, team="cockpit" if settings.shell else ("demo" if settings.worlds else None))

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

    @app.get("/api/demo/ablaeufe")
    def demo_flows():
        """The demonstrations a sample workspace offers: whole flows the surface plays step by step. They travel with the
        world they were written for (`_ablaeufe/*.json` in the template, put there by whoever built the world), so a flow
        never meets data it does not fit."""
        if not settings.demo or settings.template is None or settings.worlds:
            return {"flows": []}                         # the public demo's sandboxes cannot be put back from here
        flows = []
        for p in sorted((settings.template / "_ablaeufe").glob("*.json")):
            try:
                flows.append(json.loads(p.read_text(encoding="utf-8")))
            except ValueError:
                continue
        return {"flows": flows}

    @app.post("/api/demo/reset")
    def demo_reset(request: Request):
        """A sample workspace back to its world before a demonstration. Only where the shell named a world and its login lets
        the person in; the public demo starts over with a fresh sandbox instead."""
        if not settings.demo or settings.template is None or settings.worlds or single is None:
            raise HTTPException(404, "nothing to reset here")
        if settings.identity is not None and not settings.identity(request):
            raise HTTPException(401, "not signed in")
        from ..demo.sandbox import reset_world
        reset_world(settings.template, Path(settings.write_root or settings.root))     # no case lock: the locks live in _steps, which goes too
        return {"ok": True}

    @app.get("/api/me", response_model=MeOut)
    def me(request: Request, c: Ctx = Depends(ctx)):
        return me_out(c, getattr(request.state, "fresh_person", None) or _who(request, c.config), request)

    def connectors_of(c: Ctx) -> list[RuleConnector]:
        """The workspace's connectors, in the reader's language: a field's English twin (`<field>_en`) where there is one."""
        for place in (c.store.root / "connectors.json", c.config.dir / "connectors.json" if c.config.dir else None):
            if place and place.is_file():
                try:
                    raw = json.loads(place.read_text(encoding="utf-8")).get("connectors", [])
                    return [RuleConnector(**{k: str(item.get(f"{k}_{c.lang}") or item.get(k) or "") for k in RuleConnector.model_fields if k in item or f"{k}_{c.lang}" in item})
                            for item in raw if isinstance(item, dict) and item.get("id")]
                except (OSError, ValueError, TypeError):
                    return []
        return []

    @app.get("/api/setup", response_model=SetupOut)
    def get_setup(c: Ctx = Depends(ctx)):
        lang = c.lang
        de = lang == "de"
        # plugins: the shell's, or the demo's copy of them
        plugins: list[SetupItem] = []
        if settings.plugins is not None:
            plugins = [SetupItem(id=str(p.get("id")), name=str(p.get("name") or p.get("id")), side=str(p.get("version") or ""), text=str(p.get("text") or p.get("description") or ""))
                       for p in settings.plugins]
        else:
            f = Path(__file__).resolve().parent.parent / "demo" / "plugins.json"
            try:
                for p in json.loads(f.read_text(encoding="utf-8")).get("plugins", []):
                    t = p.get("text") or {}
                    plugins.append(SetupItem(id=p["id"], name=p["name"], side=p.get("version", ""), text=t.get(lang) or t.get("en", "") if isinstance(t, dict) else str(t)))
            except (OSError, ValueError, KeyError):
                plugins = []
        # sources: where new cases come from, the mailbox first, then the connectors
        sources: list[SetupItem] = []
        mb = c.config.theme.get("mailbox") if isinstance(c.config.theme.get("mailbox"), dict) else None
        if mb:
            sources.append(SetupItem(id="mailbox", name="Postfach" if de else "Mail inbox", side="Verbunden" if de else "Connected",
                                     text="Neue Mails werden gelesen, sobald sie ankommen, und als Fall angelegt." if de else "New mail is read as soon as it arrives and opened as a case."))
        if c.config.theme.get("mail_drop"):
            sources.append(SetupItem(id="drop", name="Mail-Ablage (.eml)" if de else "File drop (.eml)", side="Verbunden" if de else "Connected",
                                     text="Eine Mail, von Hand hereingezogen, nimmt denselben Weg wie aus dem Postfach." if de else "A mail dropped in by hand takes the same way in as one from the inbox."))
        for k in connectors_of(c):
            sources.append(SetupItem(id=k.id, name=k.name, side=k.direction, text=" · ".join(x for x in (k.carries, k.standard) if x) + (f"\n{k.note}" if k.note else "")))
        # roles: the words, and who holds each in this workspace
        words = (c.config.vocabulary.get(lang) or c.config.vocabulary.get("en") or {}).get("roles") or {}
        people = [p for p in c.config.people if p.kind == "human"]
        seen_roles = list(words) + [r for p in people for r in p.roles if r not in words]
        roles = []
        for r in dict.fromkeys(seen_roles):
            holders = [p.name_in(lang) for p in people if r in p.roles]
            w_ = str(words.get(r) or r)
            roles.append(SetupItem(id=r, name=w_[:1].upper() + w_[1:], side=", ".join(holders) or ("niemand" if de else "nobody"),
                                   text=(f"In diesem Arbeitsbereich: {', '.join(holders)}." if holders else "Diese Rolle hat hier niemand.") if de
                                   else (f"In this workspace: {', '.join(holders)}." if holders else "Nobody holds this role here.")))
        # schemas: per kind of case, the documents it collects
        schemas = []
        try:
            arts = json.loads((c.config.dir / "artifacts.json").read_text(encoding="utf-8")) if c.config.dir else {}
        except (OSError, ValueError):
            arts = {}
        files = (c.config.vocabulary.get(lang) or {}).get("files") or {}
        kinds = {e.key: e.word for l in views.config_view(c.config, lang).lists for e in l.entries}
        def doc(a: dict) -> str:
            """A document as the reader calls it; numbered photos are one entry; a file without a word is a working file, not shown."""
            f = str(a.get("file", ""))
            if f.endswith(".json") or f == "review.md":            # the record and the thread are the case itself, not something it collects
                return ""
            if re.match(r"fotos?-\d+\.", f):
                return "Fotos" if de else "Photos"
            return str(files.get(f) or "")
        def docs_of(items) -> list[str]:
            return [d for d in (doc(a) for a in items if isinstance(a, dict)) if d]
        common = docs_of(arts.get("common", []))
        for key, fmt in (arts.get("formats") or {}).items():
            if not isinstance(fmt, dict):
                continue
            docs = list(dict.fromkeys(common + docs_of(fmt.get("artifacts", []))))
            n = len(docs)
            schemas.append(SetupItem(id=key, name=str(kinds.get(key) or key), side=(f"{n} Dokumente" if de else f"{n} documents"), items=docs,
                                     text="Was ein Fall dieser Art sammelt. Die KI füllt es aus, ein Mensch prüft es." if de else "What a case of this kind collects. The AI fills it in; a person checks it."))
        return SetupOut(plugins=plugins, sources=sources, roles=roles, schemas=schemas)

    # ------------------------------------------------------------ the AI team (demo only; inside the cockpit the surface asks the shell)
    from ..domain.team import DemoTeam, TeamError
    TEAM_COOKIE = "cf_team"

    def _team(request: Request, response: Response) -> DemoTeam:
        if not settings.worlds:
            raise HTTPException(404, "The AI team lives in the cockpit here.")
        raw = request.cookies.get(TEAM_COOKIE, "")
        if "." in raw:
            tid, sig = raw.rsplit(".", 1)
            d = settings.sessions_dir / tid
            if tid.startswith("team-") and "/" not in tid and hmac.compare_digest(sig, _sign(settings.secret, tid)) and d.is_dir():
                return DemoTeam(d)
        t = DemoTeam.create(settings.sessions_dir)
        response.set_cookie(TEAM_COOKIE, f"{t.dir.name}.{_sign(settings.secret, t.dir.name)}", httponly=True, samesite="lax", max_age=settings.session_hours * 3600)
        return t

    def _team_do(fn):
        try:
            return fn()
        except TeamError as exc:
            raise HTTPException(400, str(exc))

    @app.get("/api/team")
    def team_view(request: Request, response: Response, c: Ctx = Depends(ctx)):
        return _team(request, response).view(c.lang if c.lang in ("en", "de") else "en")

    @app.post("/api/team")
    async def team_change(request: Request, response: Response, c: Ctx = Depends(ctx)):
        t, body = _team(request, response), await request.json()
        what = str(body.get("what", ""))
        if what == "hire":
            _team_do(lambda: t.hire(str(body.get("template", "")), str(body.get("model", ""))))
        elif what == "dismiss":
            _team_do(lambda: t.dismiss(str(body.get("agent", ""))))
        elif what == "logs_dir":
            _team_do(lambda: t.set_logs(str(body.get("logs_dir", ""))))
        else:
            raise HTTPException(400, f"'{what}' is not a change")
        return t.view(c.lang if c.lang in ("en", "de") else "en")

    @app.post("/api/team/sessions")
    async def team_start(request: Request, response: Response):
        t, body = _team(request, response), await request.json()
        return {"id": _team_do(lambda: t.start(str(body.get("agent", ""))))}

    @app.get("/api/team/sessions/{sid}")
    def team_session(sid: str, request: Request, response: Response, c: Ctx = Depends(ctx)):
        t = _team(request, response)
        return _team_do(lambda: t.session(sid, c.lang if c.lang in ("en", "de") else "en"))

    @app.post("/api/team/sessions/{sid}/{what}")
    async def team_act(sid: str, what: str, request: Request, response: Response, c: Ctx = Depends(ctx)):
        t, body = _team(request, response), await request.json()
        if what == "say":
            _team_do(lambda: t.say(sid, str(body.get("text", ""))))
        elif what == "end":
            _team_do(lambda: t.end(sid, str(body.get("note", ""))))
        else:
            raise HTTPException(404, f"'{what}' is not an action")
        return t.session(sid, c.lang if c.lang in ("en", "de") else "en")

    # ------------------------------------------------------------ reading
    @app.get("/api/config", response_model=views.ConfigView)
    def get_config(c: Ctx = Depends(ctx)):
        v = views.config_view(c.config, c.lang)
        v.theme = {**v.theme, "canon": (Path(c.store.root) / "_kanon").is_dir() or bool(c.config.theme.get("interview")), "demo": settings.demo, "resettable": bool(settings.demo and settings.template is not None and not settings.worlds), "samples": samples_of(c)[1] if settings.demo else [], "world": c.world, "worlds": list(settings.worlds)}
        return v

    @app.get("/api/me/turns", response_model=list[TurnOut])
    def my_turns(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        stepping.detect(c.store, c.config)
        all_cases = reading.load_all(c.store, c.config)
        seen = reads.load(c.store, who)
        return [TurnOut(case=views.card(c.config, case, who, c.lang, seen), turn=t) for case, t in whose.turns_for(who, all_cases, c.config, c.lang)]

    @app.get("/api/cases", response_model=list[GroupOut])
    def list_cases(group: str | None = None, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        stepping.detect(c.store, c.config)
        seen = reads.load(c.store, who)
        cards = [views.card(c.config, case, who, c.lang, seen) for case in reading.load_all(c.store, c.config)]
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

    @app.get("/api/me/rhythm", response_model=RhythmOut)
    def my_rhythm(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        seal_actions = {a.id for st in c.config.stages for a in st.actions if a.seal}
        now = dt.datetime.now().astimezone()
        today, week_start = now.date().isoformat(), (now - dt.timedelta(days=7)).isoformat()
        titles: dict[str, tuple[str, str]] = {}
        out = RhythmOut()
        for name in c.store.journals():
            try:
                j = c.store.read_json(f"_steps/{name}")
            except (OSError, ValueError):
                continue
            if j.get("by") != who or j.get("status") != "done" or str(j.get("created", "")) < week_start:
                continue
            seal = j.get("action") in seal_actions
            out.week_steps += 1
            out.week_seals += int(seal)
            if str(j.get("created", ""))[:10] == today:
                out.today_steps += 1
                if seal:
                    cid = str(j.get("case", ""))
                    if cid not in titles:
                        try:
                            k = reading.load(c.store, c.config, cid)
                            titles[cid] = (str(k.meta.get("title") or cid), c.config.word("labels", k.label, c.lang, k.label))
                        except (KeyError, StoreError):
                            titles[cid] = (cid, "")
                    out.today_seals.append(SealOut(case=cid, title=titles[cid][0], label=titles[cid][1],
                                                   action=c.config.word("actions", str(j.get("action")), c.lang, str(j.get("action"))), at=str(j.get("created", ""))))
        return out

    @app.get("/api/cases/{case_id}", response_model=views.CaseView)
    def get_case(case_id: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        try:
            case = reading.load(c.store, c.config, case_id)
        except (KeyError, StoreError) as exc:
            raise HTTPException(404, str(exc) or case_id)
        return views.view(c.config, case, who, c.lang, file_url, reads.load(c.store, who), c.store)

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

    @app.get("/api/videos/{name}")
    def get_video(name: str, c: Ctx = Depends(ctx)):
        """An explainer from the application's configuration (`config/<domain>/videos/`); only files the catalog names."""
        known = {x.get("file") for x in c.config.videos} | {x.get("poster") for x in c.config.videos}
        if name not in known or "/" in name or name.startswith(".") or not c.config.dir:
            raise HTTPException(404, name)
        p = (c.config.videos_dir or c.config.dir / "videos") / name
        if not p.is_file():
            raise HTTPException(404, name)
        return FileResponse(p)

    def _signal_file(c: Ctx, signal_id: str) -> Path | None:
        folder = c.store.root / "_signale"
        for f in sorted(folder.glob("*.md")) if folder.is_dir() else []:
            if f.stem == signal_id or re.search(rf"^id:\s*{re.escape(signal_id)}\s*$", f.read_text(encoding="utf-8").split("---", 2)[1] if f.read_text(encoding="utf-8").startswith("---") else "", re.M):
                return f
        return None

    @app.get("/api/signals", response_model=list[SignalOut])
    def get_signals(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """What the pattern helper noticed across the files of this world: `_signale/*.md` at the pipeline root."""
        folder = c.store.root / "_signale"
        if not folder.is_dir():
            return []
        cases_by_id = {case.id: case for case in reading.load_all(c.store, c.config)}

        def sig_case(i: str) -> SignalCase:
            case = cases_by_id.get(i)
            if case is None:
                return SignalCase(id=i, title=i)
            e = value_lists.entry(c.config.lists, "label", case.label) or {}
            return SignalCase(id=i, title=str(views.localized(case.meta, c.lang).get("title") or case.meta.get("title") or i), external_id=str(case.meta.get("external_id") or ""),
                              stage_word=c.config.word("stages", case.stage, c.lang, case.stage), color=str(e.get("color") or ""))
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
            shown, body = in_lang(head, body, c.lang)
            out.append(SignalOut(id=head.get("id", f.stem), kind=head.get("kind", ""), title=shown.get("title", f.stem), status=head.get("status", "offen"), date=head.get("date", ""),
                                 cases=[sig_case(i) for i in ids], text=body.strip(), decided_by=head.get("decided_by", ""), decided_at=head.get("decided_at", "")))
        return out

    @app.post("/api/signals/{signal_id}/status", response_model=SignalOut)
    def post_signal_status(signal_id: str, body: SignalStatusIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """A person moves a hint: looking into it, done (nothing to do, or handled), or back to open. The hint itself is never
        changed or deleted; only its status, with who and when, in its header."""
        me = c.config.person(who)
        if not me or me.kind != "human":
            raise HTTPException(403, "a person decides what follows from a hint")
        f = _signal_file(c, signal_id)
        if f is None:
            raise HTTPException(404, signal_id)
        rel = str(f.relative_to(c.store.root))
        with c.store.lock(f"_signal-{signal_id}"):
            text = f.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            if not text.startswith("---") or len(parts) < 3:
                raise HTTPException(409, "this hint has no header to keep its status in")
            lines = [l for l in parts[1].strip("\n").splitlines() if not re.match(r"^(status|decided_by|decided_at):", l)]
            stamp = dt.datetime.now().astimezone().isoformat(timespec="minutes")
            lines += [f"status: {body.status}", f"decided_by: {me.name}", f"decided_at: {stamp}"]
            c.store.write_atomic(rel, "---\n" + "\n".join(lines) + "\n---" + parts[2])
        return next(s for s in get_signals(c, who) if s.id == signal_id)

    @app.get("/api/canon")
    def get_canon(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """The house canon at one glance: every document by layer and depth, with scope, status, owner, origin."""
        from ..domain import house
        return house.overview(c.store)

    @app.get("/api/canon/doc")
    def get_canon_doc(file: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """One document of the house canon, rendered. Only files under `_kanon/`."""
        from ..domain import house
        from .text import render
        try:
            text = house.doc_text(c.store, file)
        except FileNotFoundError:
            raise HTTPException(404, file)
        return {"file": file, "html": render(text, "md" if file.endswith(".md") else "plain")}

    @app.get("/api/rules", response_model=RulesOut)
    def get_rules(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
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
        from ..domain import rulebook
        modules = []

        def module_out(mid: str, m: dict, d: dict | None, in_force: bool) -> RuleModule:
            m = in_lang(m, m.get("body", ""), c.lang)[0]
            if d is not None:
                d = in_lang(d, d.get("body", ""), c.lang)[0]
            return RuleModule(id=mid, kind=m.get("kind", ""), title=m.get("title", mid), version=int(m.get("version") or 1),
                              status=m.get("status", ""), approved_by=m.get("approved_by", ""), date=m.get("date", ""), text=m.get("body", ""),
                              areas=rulebook.areas_of(m), draft=int(d["version"]) if d else None, versions=len(rulebook.history(c.store, mid)),
                              in_force=in_force, use=m.get("use", ""), source=(d or m).get("source", "") or m.get("source", ""),
                              draft_text=(d or {}).get("body", ""), draft_title=(d or {}).get("title", ""), draft_areas=rulebook.areas_of(d) if d else [],
                              draft_by=(d or {}).get("drafted_by", ""), draft_date=(d or {}).get("date", ""), draft_note=(d or {}).get("note", ""))
        for mid, m in rulebook.current(c.store).items():
            modules.append(module_out(mid, m, rulebook.draft_of(c.store, mid), True))
        for mid, d in rulebook.proposed(c.store).items():
            modules.append(module_out(mid, d, d, False))
        connectors = connectors_of(c)
        from ..domain import handoff
        tg = handoff.targets(c.store)
        loc = lambda d, k: (d.get(k) or {}).get(lang) or (d.get(k) or {}).get("en") or "" if isinstance(d.get(k), dict) else str(d.get(k) or "")
        matrix = [MatrixRow(id=r["id"], kind=str(r.get("kind", "")), word=loc(r, "word") or str(r.get("kind", "")), when=loc(r, "when"), action=str(r.get("action", "")),
                            action_word=loc(r, "action_word") or str(r.get("action", "")), target=str(r.get("target", "")),
                            target_word=str((tg.get(r.get("target", "")) or {}).get("label", "")), approval=str(r.get("approval", "human")),
                            connected=handoff.connected(c.store, r))
                  for r in handoff.matrix(c.store, c.config)]
        me = c.config.person(who)
        human = bool(me and me.kind == "human")
        label = value_lists.for_field(c.config.lists, "label") or {}
        areas = [RuleArea(key=str(e.get("key")), word=value_lists.in_lang(e.get("word"), lang, c.config.word("labels", str(e.get("key")), lang, str(e.get("key")))),
                          color=str(e.get("color") or "")) for e in value_lists.offered(label)] if label else \
                [RuleArea(key=k, word=c.config.word("labels", k, lang, k)) for k in ((c.config.vocabulary.get(lang) or {}).get("labels") or {})]
        return RulesOut(stages=stages, skills=skills, modules=modules, connectors=connectors, matrix=matrix,
                        may_edit=human and "operator" in me.roles, may_decide=human and bool(set(me.roles) & {"operator", "approver"}),
                        areas=areas, me=me.name if me else "")

    # ------------------------------------------------------------ the rulebook, edited as versions (request 9, ADR-026)
    def _version(m: dict | None, lang: str = "") -> ModuleVersion | None:
        from ..domain import rulebook
        if not m:
            return None
        if lang:
            m = in_lang(m, m.get("body", ""), lang)[0]
        return ModuleVersion(version=int(m.get("version") or 0), status=m.get("status", ""), title=m.get("title", ""), text=m.get("body", ""),
                             areas=rulebook.areas_of(m), date=m.get("date", ""), approved_by=m.get("approved_by", ""),
                             drafted_by=m.get("drafted_by", ""), note=m.get("note", ""), source=m.get("source", ""), reason=m.get("reason", ""))

    def _history(c: Ctx, who: str, module_id: str) -> ModuleHistory:
        from ..domain import rulebook
        now, d = rulebook.current(c.store).get(module_id), rulebook.draft_of(c.store, module_id)
        me = c.config.person(who)
        human = bool(me and me.kind == "human")
        return ModuleHistory(id=module_id, in_force=_version(now, c.lang), draft=_version(d, c.lang), versions=[_version(v, c.lang) for v in rulebook.history(c.store, module_id)],
                             may_edit=human and "operator" in me.roles,
                             may_approve=bool(d and human and set(me.roles) & {"operator", "approver"} and d.get("drafted_by") != me.name))

    def _rulebook_refused(exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"ok": False, "reason": str(exc)})

    @app.get("/api/rulebook/{module_id}", response_model=ModuleHistory)
    def get_module(module_id: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        h = _history(c, who, module_id)
        if not h.versions:
            raise HTTPException(404, module_id)
        return h

    @app.post("/api/rulebook/{module_id}/draft", response_model=ModuleHistory)
    def post_module_draft(module_id: str, body: DraftIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """A change as a draft: a new version, or the open draft written over. A new id starts a new module."""
        from ..domain import rulebook
        try:
            rulebook.save_draft(c.store, c.config, module_id, who, body.text, body.title, body.kind, body.areas, body.note)
        except rulebook.RulebookError as exc:
            return _rulebook_refused(exc)
        return _history(c, who, module_id)

    @app.post("/api/rulebook/{module_id}/approve", response_model=ModuleHistory)
    def post_module_approve(module_id: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """The open draft comes into force; four eyes. Cases that started before keep the version they started with."""
        from ..domain import rulebook
        try:
            rulebook.approve(c.store, c.config, module_id, who)
        except rulebook.RulebookError as exc:
            return _rulebook_refused(exc)
        return _history(c, who, module_id)

    @app.post("/api/rulebook/{module_id}/reject", response_model=ModuleHistory)
    def post_module_reject(module_id: str, body: RejectIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """A proposed change not taken: it stays on record as rejected, with the reason. What was in force stays in force."""
        from ..domain import rulebook
        try:
            rulebook.reject(c.store, c.config, module_id, who, body.reason)
        except rulebook.RulebookError as exc:
            return _rulebook_refused(exc)
        return _history(c, who, module_id)

    @app.post("/api/rulebook/{module_id}/retire", response_model=ModuleHistory)
    def post_module_retire(module_id: str, body: RetireIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """Out of force, as a version of its own with the reason. Nothing is deleted."""
        from ..domain import rulebook
        try:
            rulebook.retire(c.store, c.config, module_id, who, body.note)
        except rulebook.RulebookError as exc:
            return _rulebook_refused(exc)
        return _history(c, who, module_id)

    # ------------------------------------------------------------ value lists (SYS-105): read by all, changed by the operators
    from ..domain import lists as value_lists

    def _lists_out(c: Ctx, who: str) -> ListsOut:
        p = c.config.person(who)
        return ListsOut(may_edit=bool(p and "operator" in p.roles), lists=views.list_views(c.config, c.lang, value_lists.counts(c.store, c.config.lists)))

    def _lists_refused(c: Ctx, who: str) -> JSONResponse | None:
        p = c.config.person(who)
        if p and "operator" in p.roles:
            return None
        return JSONResponse(status_code=403, content={"ok": False, "reason": c.config.word("texts", "lists_refused", c.lang, "Only the people who run this place change its lists.")})

    def _list_view(c: Ctx, list_id: str) -> views.ListView:
        counts = value_lists.counts(c.store, c.config.lists)
        return next(v for v in views.list_views(c.config, c.lang, counts) if v.id == list_id)

    @app.get("/api/lists", response_model=ListsOut)
    def get_lists(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        return _lists_out(c, who)

    @app.post("/api/lists", response_model=ListChangeOut)
    def post_list(body: ListIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """Start a list (id, name, the field it fills, whether a new case asks for it), or change one's name or asking."""
        if (refused := _lists_refused(c, who)) is not None:
            return refused
        if not stepping.STEP_ID.match(body.step_id):
            return _refuse(Exception("step id must be 1–80 letters, digits, '-' or '_'"))
        try:
            line = value_lists.put_list(c.store, c.config, who, body.id.strip(), body.word, body.field, body.on_create, body.step_id)
        except value_lists.ListError as exc:
            return _refuse(exc)
        return ListChangeOut(ok=True, line=line, list=_list_view(c, line["list"]))

    @app.post("/api/lists/{list_id}/entries", response_model=ListChangeOut)
    def post_list_entry(list_id: str, body: ListEntryIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """Add an entry, or change one's name, colour, description or status. Written to the tree's lists.json, one line in _lists/log.jsonl."""
        if (refused := _lists_refused(c, who)) is not None:
            return refused
        if not stepping.STEP_ID.match(body.step_id):
            return _refuse(Exception("step id must be 1–80 letters, digits, '-' or '_'"))
        try:
            line = value_lists.put_entry(c.store, c.config, who, list_id, body.key, body.word, body.color, body.description, body.status, body.step_id)
        except value_lists.ListError as exc:
            return _refuse(exc)
        return ListChangeOut(ok=True, line=line, list=_list_view(c, list_id))

    @app.get("/api/stages", response_model=list[StageOut])
    def stages(c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        out, seen = [], reads.load(c.store, who)
        for folder in c.store.stages():
            st = c.config.stage(folder)
            cards = [views.card(c.config, reading.load(c.store, c.config, cid), who, c.lang, seen) for cid in c.store.cases(folder)]
            out.append(StageOut(folder=folder, key=st.key if st else "", word=c.config.word("stages", folder, c.lang, folder),
                                station=c.config.word("stations", st.key, c.lang, "") if st and st.key else "", cases=cards))
        return out

    # ------------------------------------------------------------ writing: every write is a step
    def _step(c: Ctx, case_id: str, req: StepRequest, who: str) -> StepResult:
        """Every step from the surface carries the viewer's language, so a helper it orders writes in it (request 8)."""
        if "_lang" not in req.payload:
            req = req.model_copy(update={"payload": {**req.payload, "_lang": c.lang}})
        return stepping.step(c.store, c.config, case_id, req, who)

    def _answer(result: StepResult) -> JSONResponse:
        return JSONResponse(status_code=200 if result.ok else 409, content=result.model_dump(by_alias=True))

    def _connect(request: Request, response: Response, c: Ctx) -> None:
        """In the public demo, a world that hands cases on (the inbox) is connected to the visitor's own sandboxes of the
        worlds it names, made on the spot when missing: `targets.json` in its sandbox, as the cockpit writes it for real."""
        if not settings.worlds or not c.world or not settings.worlds[c.world].targets:
            return
        mapping = _read_worlds(request)
        if c.session:
            mapping[c.world] = c.session
        out = {}
        for key, name in settings.worlds[c.world].targets.items():
            if name not in settings.worlds:
                continue
            other = _session_ctx(mapping[name]) if name in mapping else None
            if other is None:
                other = _new_session(name)
                mapping[name] = other.session
            out[key] = {"label": other.config.name, "root": str(other.store.root), "config": str(settings.worlds[name].config_dir),
                        "url": "", "external_prefix": "SN-" if name == "claims" else ""}
        c.store.write_json("targets.json", out)
        _set_worlds(response, mapping)

    @app.post("/api/cases/{case_id}/steps", response_model=StepResult)
    def post_step(case_id: str, body: StepRequest, request: Request, response: Response, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        _connect(request, response, c)
        result = _step(c, case_id, body, who)
        if result.ok and not result.replayed:
            action = next((a for st in c.config.stages for a in st.actions if a.id == body.action and a.handover), None)
            if action:
                _handover(request, response, c, case_id, action.handover, body.step_id)
        answer = _answer(result)
        for k, v in response.headers.items():        # cookies the hand-over set travel with the JSON answer
            if k.lower() == "set-cookie":
                answer.headers.append(k, v)
        return answer

    @app.post("/api/cases/{case_id}/seen", response_model=SeenOut)
    def post_seen(case_id: str, body: SeenIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """Read or unread for the viewer alone (domain/seen.py). The surface sends it when a case is opened, and from
        "Mark as unread". Not a step: nothing in the case changes."""
        try:
            case = reading.load(c.store, c.config, case_id)
        except (KeyError, StoreError) as exc:
            raise HTTPException(404, str(exc) or case_id)
        try:
            return SeenOut(case=case_id, unread=reads.mark(c.store, c.config, case, who, body.unread))
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.post("/api/cases/{case_id}/entries", response_model=StepResult)
    def post_entry(case_id: str, body: EntryIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        if body.kind not in ("note", "answer", "done"):
            raise HTTPException(422, "kind must be note, answer or done")
        payload = {"text": body.text, "resolves": body.resolves or "", "for": body.for_ or "", "title": body.title or ""}
        return _answer(_step(c, case_id, StepRequest(action=body.kind, step_id=body.step_id, payload=payload), who))

    @app.post("/api/cases/{case_id}/translate", response_model=TranslateOut)
    def post_translate(case_id: str, body: TranslateIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """"Show translation": the helper `translate` writes `<stem>.<lang>.md` beside the original, which stays as it
        came. Once there, the same request answers at once. A background order: no thread entry, nobody's move."""
        try:
            case = reading.load(c.store, c.config, case_id)
        except (KeyError, StoreError) as exc:
            raise HTTPException(404, str(exc) or case_id)
        lang = (body.lang or c.lang or "").lower()
        if not re.fullmatch(r"[a-z]{2}", lang):
            raise HTTPException(422, "lang must be two letters")
        stem, dot, ext = body.file.rpartition(".")
        if body.file not in case.files or "/" in body.file or f".{ext}" not in views.TRANSLATABLE or views.LANG_FILE.match(body.file):
            raise HTTPException(404, f"no text file '{body.file}' in this case")
        out = f"{stem}.{lang}.md"
        if out in case.files:
            return TranslateOut(original=body.file, lang=lang, name=out, ready=True)
        person = c.config.person(who)
        refusal = runs_.may_order(c.config, "translate", person) if person else "not a person of this application"
        if refusal:
            raise HTTPException(409, refusal)
        run = runs_.order(c.store, c.config, case_id, case.stage, "translate", who, f"{body.file} → {lang}", request_id=body.request_id,
                          background=True, lang=lang, extra={"file": body.file, "out": out})
        return TranslateOut(original=body.file, lang=lang, name=out, ready=False, run=run)

    @app.post("/api/cases/{case_id}/runs", response_model=StepResult)
    def post_run(case_id: str, body: RunIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        return _answer(_step(c, case_id, StepRequest(action="ask", step_id=body.request_id, payload={"skill": body.skill, "text": body.note}), who))

    @app.post("/api/cases/{case_id}/assets", response_model=AssetOut)
    async def post_asset(case_id: str, slot: str = Form(...), step_id: str = Form(...), file: UploadFile = File(...), c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        data = await file.read()
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"larger than {settings.max_upload_mb} MB")
        prior = stepping.read_journal(c.store, step_id)
        if prior is not None:
            return AssetOut(name=str(prior.payload.get("files", [""])[0]), slot=slot, step=_step(c, case_id, StepRequest(action="deliver", step_id=step_id), who))
        try:
            name = assets.put(c.store, c.config, case_id, slot, data, file.filename or "")
        except StoreError as exc:
            raise HTTPException(409, str(exc))
        return AssetOut(name=name, slot=slot, step=_step(c, case_id, StepRequest(action="deliver", step_id=step_id, payload={"files": [name], "title": ""}), who))

    @app.post("/api/cases/{case_id}/samples", response_model=AssetOut)
    def post_sample(case_id: str, body: SampleIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """The demo's 'put the sample invoice in': a bundled file lands in the slot as a delivered version."""
        samples_dir, samples = samples_of(c)
        source = body.source or body.slot
        if not settings.demo or not samples_dir or source not in samples:
            raise HTTPException(404, "no sample for that slot")
        prior = stepping.read_journal(c.store, body.step_id)
        if prior is not None:
            return AssetOut(name=str(prior.payload.get("files", [""])[0]), slot=body.slot, step=_step(c, case_id, StepRequest(action="deliver", step_id=body.step_id), who))
        try:
            name = assets.put(c.store, c.config, case_id, body.slot, samples_dir / source, source)
        except StoreError as exc:
            raise HTTPException(409, str(exc))
        return AssetOut(name=name, slot=body.slot, step=_step(c, case_id, StepRequest(action="deliver", step_id=body.step_id, payload={"files": [name]}), who))

    @app.put("/api/cases/{case_id}/vorort")
    def put_onsite(case_id: str, body: OnsiteIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """The on-site view's working state (theme.onsite.state), merged: a photo's view, a hint ticked or answered. State, not a
        deliverable version — the photos and the note are the versioned files; this only says what they are and what is settled."""
        conf = c.config.theme.get("onsite") or {}
        name = str(conf.get("state") or "")
        if not name:
            raise HTTPException(404, "this application has no on-site view")
        if any(not re.fullmatch(r"[a-z0-9-]+(\.v\d+)?\.(jpg|jpeg|png|webp)", f) or len(v) > 40 for f, v in body.photos.items()):
            raise HTTPException(422, "a photo is named by its file, a view by a short word")
        if any(len(k) > 60 or len(str(h.get("text", ""))) > 2000 for k, h in body.hints.items()):
            raise HTTPException(422, "a hint answer is at most 2000 characters")
        with c.store.lock(case_id):
            stage = c.store.find(case_id)
            if stage is None:
                raise HTTPException(404, "case not found")
            try:
                doc = json.loads(c.store.case_text(case_id, name))
            except (OSError, ValueError):
                doc = {}
            doc.setdefault("photos", {}).update(body.photos)
            for k, h in body.hints.items():
                doc.setdefault("hints", {})[k] = {"done": bool(h.get("done")), "text": str(h.get("text", "")).strip(), "by": who,
                                                  "at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
            c.store.write_json(f"{stage}/{case_id}/{name}", doc)
        return {"ok": True, "state": doc}

    # ------------------------------------------------------------ a conversation (Gatehouse and anything shaped like it)
    from ..domain import interview as talk

    def _talk_case(c: Ctx, case_id: str) -> Case:
        try:
            return reading.load(c.store, c.config, case_id)
        except (KeyError, StoreError) as exc:
            raise HTTPException(404, str(exc) or case_id)

    def _talk_conf(c: Ctx) -> dict:
        return {"helper": "", "draft": "", "decisions": "", "findings": "", **(c.config.theme.get("interview") or {})}

    def _refuse(exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"ok": False, "reason": str(exc)})

    @app.get("/api/cases/{case_id}/interview", response_model=InterviewOut)
    def get_interview(case_id: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        case = _talk_case(c, case_id)
        name = talk.interview_file(c.config, case)
        if not name:
            raise HTTPException(404, "this case holds no conversation")
        try:
            pack = talk.load_pack(c.store.root, str(case.meta.get("pack", "")))
        except talk.InterviewError as exc:
            raise HTTPException(404, str(exc))
        total = len(talk.question_ids(pack))
        doc = case.data.get(name) or {}
        st = c.config.stage(case.stage)
        asked = talk.respondents(c.config, case)
        helper_runs = [r for r in case.runs if r.background and r.requested_by == who and r.status in ("queued", "running")]
        people = []
        viewer_p = c.config.person(who)
        sees_all = bool(viewer_p and {"moderator", "decider"} & set(viewer_p.roles))     # respondents never see a ranking of their colleagues
        others_done = 0
        for pid, pr in talk.progress(c.config, case, total).items():
            p = c.config.person(pid)
            if pid != who and not sees_all:
                others_done += pr["done"]
                continue
            people.append(RespondentOut(id=pid, name=p.name if p else pid, answered=pr["answered"], total=total, done=pr["done"], me=pid == who))
        mine = {q: {k: v for k, v in a.items() if k != "step"} for q, a in (doc.get("answers", {}).get(who) or {}).items()}
        return InterviewOut(case=case.id, title=str(case.meta.get("title") or case.id), pack=pack, me=who,
                            can_answer=bool(st and st.interview and who in asked), anchor=str((doc.get("anchor") or {}).get(who, "")),
                            answers=mine, followup_answers={f: {k: v for k, v in a.items() if k != "step"} for f, a in (doc.get("followups", {}).get(who) or {}).items()},
                            helper=case.data.get(f"nachfragen-{who}.json") or {}, helper_running=bool(helper_runs),
                            done=bool((doc.get("done") or {}).get(who)), respondents=people, sees_all=sees_all,
                            others=len(asked) - (1 if who in asked else 0) if not sees_all else 0, others_done=others_done)

    @app.post("/api/cases/{case_id}/interview/answer")
    def post_answer(case_id: str, body: AnswerIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        try:
            return {"ok": True, "answer": talk.answer(c.store, c.config, case_id, who, body.question, body.text, body.marker, body.step_id)}
        except talk.InterviewError as exc:
            return _refuse(exc)

    @app.post("/api/cases/{case_id}/interview/anchor")
    def post_anchor(case_id: str, body: AnchorIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        try:
            return {"ok": True, "anchor": talk.anchor(c.store, c.config, case_id, who, body.text)}
        except talk.InterviewError as exc:
            return _refuse(exc)

    @app.post("/api/cases/{case_id}/interview/followup")
    def post_followup(case_id: str, body: FollowupIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        try:
            return {"ok": True, "answer": talk.followup(c.store, c.config, case_id, who, body.followup, body.text, body.step_id)}
        except talk.InterviewError as exc:
            return _refuse(exc)

    @app.post("/api/cases/{case_id}/interview/chapter")
    def post_chapter(case_id: str, body: ChapterIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        try:
            return {"ok": True, "run": talk.chapter(c.store, c.config, case_id, who, body.block, _talk_conf(c)["helper"], body.step_id)}
        except talk.InterviewError as exc:
            return _refuse(exc)

    @app.post("/api/cases/{case_id}/interview/finish")
    def post_finish(case_id: str, body: FinishIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        try:
            first = talk.finish(c.store, c.config, case_id, who, body.step_id)
        except talk.InterviewError as exc:
            return _refuse(exc)
        if first:
            p = c.config.person(who)
            with c.store.lock(case_id):
                stage = c.store.find(case_id)
                stepping._append_entry(c.store, c.config, case_id, stage, {"author": p.name if p else who, "status": "info",
                                       "title": c.config.word("texts", "interview_done", c.lang, "Done with the conversation"), "text": c.config.word("texts", "interview_done_text", c.lang, "My answers are in."), "step": body.step_id})
        return {"ok": True, "first": first}

    @app.get("/api/cases/{case_id}/outcome", response_model=OutcomeOut)
    def get_outcome(case_id: str, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        case = _talk_case(c, case_id)
        conf = _talk_conf(c)
        try:
            pack = talk.load_pack(c.store.root, str(case.meta.get("pack", "")))
            blocks = [{"id": b["id"], "title": b["title"], "canon": b.get("canon", "")} for b in pack["blocks"]]
        except talk.InterviewError:
            blocks = []
        decided = case.data.get(conf["decisions"]) or {}
        lines = [{**x, "decision": {k: v for k, v in (decided.get(str(x.get("id"))) or {}).items() if k != "step"}} for x in (case.data.get(conf["draft"]) or {}).get("lines", [])]
        p = c.config.person(who)
        stage = c.config.stage(case.stage)
        can = bool(p and "decider" in p.roles and stage and any(r.startswith("decided:") for a in stage.actions for r in a.requires))
        canon = reading.newest_versions(case.files).get("canon.md")
        last = case.last_run
        return OutcomeOut(case=case.id, title=str(case.meta.get("title") or case.id), stage_word=c.config.word("stages", case.stage, c.lang, case.stage), blocks=blocks,
                          findings=case.data.get(conf["findings"]) or {}, lines=lines, can_decide=can,
                          open_lines=len([x for x in lines if not x["decision"].get("verdict")]), canon=canon, canon_url=file_url(case, canon) if canon else None,
                          running=bool(last and last.status in ("queued", "running")),
                          people={x.id: x.name for x in c.config.people}, subtitle=str(case.meta.get("subtitle") or ""),
                          version=max(1, reading.split_version(canon)[1]) if canon else 0,
                          approved_by=(lambda p: p.name if p else "")(c.config.person(max(decided.values(), key=lambda d: str(d.get("at", ""))).get("by", "")) if decided else None),
                          approved_at=max((str(d.get("at", "")) for d in decided.values()), default=""),
                          canon_map=talk.canon_map(c.store, case.id))

    @app.post("/api/cases/{case_id}/outcome/decide")
    def post_decide(case_id: str, body: DecideIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        conf = _talk_conf(c)
        try:
            return {"ok": True, "decision": talk.decide(c.store, c.config, case_id, who, body.line, body.verdict, body.text, body.step_id, conf["draft"], conf["decisions"])}
        except talk.InterviewError as exc:
            return _refuse(exc)

    @app.post("/api/mail", response_model=NewCaseOut)
    async def post_mail(file: UploadFile = File(...), c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """A mail dropped in by hand (.eml): the same way in as from the mailbox, so the demo and the real thing are one path."""
        from ..connectors import mailbox
        p = c.config.person(who)
        if not c.config.theme.get("mail_drop"):
            raise HTTPException(404, "mails are not dropped in here")
        if not p or "operator" not in p.roles:
            return _refuse(Exception(c.config.word("texts", "mail_refused", c.lang, "Only the inbox's operators put mail in.")))
        raw = await file.read()
        if not raw or len(raw) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, "empty or too large")
        try:
            cid, _ = mailbox.ingest(c.store, c.config, raw, by=who, source="drop")
        except StoreError as exc:
            return _refuse(exc)
        return NewCaseOut(id=cid, stage=c.store.find(cid) or "")

    @app.post("/api/cases", response_model=NewCaseOut)
    def post_case(body: NewCaseIn, c: Ctx = Depends(ctx), who: str = Depends(viewer)):
        """A new case in the first stage, when the domain says how one starts (`theme.create`: label, roles, and what the meta carries)."""
        create = c.config.theme.get("create") or {}
        p = c.config.person(who)
        if not create:
            raise HTTPException(404, "new cases are not started here")
        if not p or not (set(create.get("roles", [])) & set(p.roles)):
            return _refuse(Exception(c.config.word("texts", "create_refused", c.lang, "You may not start a case here.")))
        title = body.title.strip()[:120]
        if not title:
            return _refuse(Exception(c.config.word("texts", "create_empty", c.lang, "Give it a name.")))
        from ..domain import lists as chosen
        try:
            values = chosen.validate_choice(c.config.lists, body.values)       # what the lists that ask for it gave: field → key
        except chosen.ListError as exc:
            return _refuse(exc)
        label = values.get("label") or body.label or create.get("label", "X")
        first = create.get("stage") or next((s.folder for s in c.config.stages if s.group != "archive"), None)   # where a new case starts
        if not first or first not in c.store.stages():
            return _refuse(Exception("the first stage folder is missing"))
        for prior in c.store.journals():                        # the same step id twice is the same case
            j = c.store.read_json(f"_steps/{prior}")
            if j.get("step_id") == body.step_id and j.get("action") == "create":
                return NewCaseOut(id=j["case"], stage=c.store.find(j["case"]) or first)
        from ..domain import numbering
        number = numbering.next_number(c.store, label, create.get("number"), values)   # the domain's own rule: in a year, in a series, or a placeholder
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}))).strip("-")[:40] or "akte"
        cid = f"{label}-{number}-{slug}"
        try:
            c.store.mkcase(first, cid)
        except StoreError as exc:
            return _refuse(exc)
        meta = {"configVersion": c.config.config_version, "label": label, "number": number, "title": title, "created": _now()[:10], "created_by": p.id,
                **{k: v for k, v in (create.get("meta") or {}).items()}, **values}
        if create.get("external_id"):                           # the domain's outside reference, from the same number: SN-{year}-{seq:05}
            from ..domain import handoff
            m = re.match(r"^(?:(\d{4})-)?\D*?(\d+)$", number)
            meta["external_id"] = handoff.fill(str(create["external_id"]), {**values, "number": number, "year": (m.group(1) if m and m.group(1) else str(dt.date.today().year)), "seq": (m.group(2) if m else number)})
        c.store.write_json(f"{first}/{cid}/meta.json", meta)
        c.store.write_json(f"_steps/{body.step_id}.json", {"step_id": body.step_id, "case": cid, "action": "create", "by": p.id, "status": "done", "created": _now(), "payload": {"title": title}})
        stepping._append_entry(c.store, c.config, cid, first, {"author": p.name, "status": "info", "title": c.config.word("texts", "created", c.lang, "Started"), "text": title, "step": body.step_id})
        return NewCaseOut(id=cid, stage=first)

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

        @app.get("/manifest.webmanifest", include_in_schema=False)
        def manifest(request: Request):
            """Put on a tablet's home screen, the app opens where it was added — this mount, not the host's root."""
            prefix = str(request.scope.get("root_path", "") or "").rstrip("/")
            name = single.config.name if single else "casefile"
            return JSONResponse({"name": name, "short_name": name[:24], "start_url": f"{prefix}/", "scope": f"{prefix}/", "display": "standalone",
                                 "background_color": "#F6F3EE", "theme_color": "#F6F3EE",
                                 "icons": [{"src": f"{prefix}/icon-512.png", "sizes": "512x512", "type": "image/png"},
                                           {"src": f"{prefix}/icon.svg", "sizes": "any", "type": "image/svg+xml"}]},
                                media_type="application/manifest+json")

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
                                   worlds={name: w for name, w in {         # in the design's order; a world not built yet is left out
                                       "inbox": World(config_dir=here / "config" / "posteingang", template=worlds_dir / "inbox", person="du", lang="de",
                                                      targets={"schadenakte": "claims", "angebot": "quotes", "pressroom": "pressroom"}),
                                       "quotes": World(config_dir=here / "config" / "angebot", template=worlds_dir / "quotes", person="du", lang="de"),
                                       "claims": World(config_dir=here / "config" / "claims-demo", template=worlds_dir / "claims", person="du", lang="de"),
                                       "egutachten": World(config_dir=here / "config" / "egutachten", template=worlds_dir / "egutachten", person="du", lang="de"),
                                       "pressroom": World(config_dir=here / "config" / "pressroom", template=worlds_dir / "pressroom", person="chris", lang="en"),
                                   }.items() if w.template.is_dir()},
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
