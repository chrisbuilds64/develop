"""What the surface receives: cards, the case view, the configuration in words. Built from the domain, never from the folder directly."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from ..config import DomainConfig
from ..domain import depends
from ..domain import facets
from ..domain import lists as value_lists
from ..domain.depends import Dependency
from ..domain import seen as reads
from ..domain import step as stepping
from ..domain import turn as whose
from ..models import Case, Entry, Run, Turn


class VersionView(BaseModel):
    name: str
    version: int
    size: int
    url: str


class PersonView(BaseModel):
    id: str
    name: str
    kind: str
    roles: list[str]


class SlotView(BaseModel):
    file: str
    word: str
    shape: str
    required: bool
    due_station: str
    by: str
    by_word: str
    versions: list[VersionView]
    present: bool


class CaseCard(BaseModel):
    id: str
    title: str
    label: str
    label_word: str
    stage: str
    stage_word: str
    station: str
    station_index: int
    group: str
    group_word: str
    since: str
    date: str = ""
    turn: Turn | None = None                              # the main move
    mine: bool = False                                    # the viewer is the actor of the main move
    external_id: str = ""                                 # the number the house's own system knows this case by
    external_url: str = ""                                # a link into that system, from the theme's url template
    number: str = ""                                      # the short number on the cover (meta.number)
    tint: str = ""                                        # the cover's colour, from theme.covers (by one meta key)
    party: str = ""                                       # who the case is from, for the first column of a row: reported_by, client, the mail's sender
    unread: bool = False                                  # new to the viewer: never opened, or somebody else wrote since (domain/seen.py)
    data_point: str = ""                                  # an instance over several data points: where this case lies ("Private", "Team"), REQ-005 PV-05
    values: dict[str, str] = {}                           # what the case carries for each facet (domain/facets.py): filter, sort, card


class StationView(BaseModel):
    key: str
    word: str
    state: str                                            # done | current | todo


class GroupView(BaseModel):
    key: str
    word: str


LANG_FILE = re.compile(r"^(?P<stem>.+)\.(?P<lang>[a-z]{2})\.md$")
TRANSLATABLE = (".md", ".txt", ".eml")


def localized(doc: dict, lang: str) -> dict:
    """Content in the viewer's language (request 8): a helper writes the original's language into the document and,
    per further language, `i18n.<lang>` with the same keys (title, subtitle, summary, fields …). The viewer's
    language wins key by key; `lang` keeps saying which language the original is in."""
    if not isinstance(doc, dict):
        return doc
    over = (doc.get("i18n") or {}).get(lang) if isinstance(doc.get("i18n"), dict) else None
    if not isinstance(over, dict):
        return doc
    out = {**doc}
    for k, v in over.items():
        out[k] = {**out[k], **v} if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out



def entries_in(entries: list, over) -> list:
    """The thread in the viewer's language: `i18n.<lang>.entries.<id>` gives an entry's title and text there (request 8)."""
    if not isinstance(over, dict):
        return entries
    return [e.model_copy(update={k: v for k, v in (over.get(e.id) or {}).items() if k in ("title", "text") and v}) for e in entries]


def names_in(config: DomainConfig, entries: list, lang: str) -> list:
    """Who wrote an entry and whom it is for, as the people file names them in the viewer's language ("Du" → "You").
    After the actors are known, since those are found by the name as written."""
    def name(n: str | None) -> str | None:
        if not n:
            return n
        p = config.person(n)
        return p.name_in(lang) if p is not None else n
    return [e.model_copy(update={"author": name(e.author), "for_": name(e.for_)}) for e in entries]


def translations(files: list[str]) -> dict[str, dict[str, str]]:
    """`mail.md` and `mail.en.md` beside it: the original → {language: its translation}. The original is never replaced."""
    names = set(files)
    out: dict[str, dict[str, str]] = {}
    for f in files:
        m = LANG_FILE.match(f)
        if not m:
            continue
        orig = next((m["stem"] + ext for ext in TRANSLATABLE if m["stem"] + ext in names), None)
        if orig:
            out.setdefault(orig, {})[m["lang"]] = f
    return out


def actor_of(config: DomainConfig, author: str) -> str:
    """'ai' when an agent of this application wrote the entry, 'system' for the core itself, else 'person'."""
    p = config.person(author)
    if p is not None:
        return "ai" if p.kind == "agent" else "person"
    a = (author or "").strip().lower()
    if a in ("claude", "ki", "ai") or a in (config.run_policy.get("skills") or {}):
        return "ai"
    return "system" if a in ("", "system") else "person"


def with_actors(config: DomainConfig, entries: list[Entry]) -> list[Entry]:
    """Derived for the surface: who made each entry, and which later entries undo or correct it (ADR-025)."""
    later: dict[str, list[str]] = {}
    for e in entries:
        if e.corrects:
            later.setdefault(e.corrects, []).append(e.id)
    return [e.model_copy(update={"actor": actor_of(config, e.author), "corrected_by": later.get(e.id, [])}) for e in entries]


class PhaseView(BaseModel):
    key: str
    word: str


class HelperView(BaseModel):
    """A helper at work on this case, as far as anybody can know: the phases its skill declares (run-policy `phases`), the
    one it reached, what it does right now and just did — and how long such a run usually takes."""
    run: str
    skill: str
    skill_word: str
    status: str                                           # queued | running
    created: str = ""
    started: str = ""
    phases: list[PhaseView] = Field(default_factory=list)
    phase: int = -1                                       # index into phases; -1 = none reached yet
    now: str = ""                                         # the tool call going on ("Edit web/look.css")
    recent: list[str] = Field(default_factory=list)
    steps: int = 0
    expected_s: float | None = None                       # the median of this skill's finished runs here; None without history


_EXPECTED: dict[tuple, tuple[int, float | None]] = {}


def expected_seconds(store, skill: str) -> float | None:
    """The median duration of this skill's finished runs in this tree. Read again only when the queue changed."""
    if store is None or not hasattr(store, "runs"):
        return None
    names = store.runs()
    key = (str(getattr(store, "root", "")), skill)
    hit = _EXPECTED.get(key)
    if hit and hit[0] == len(names):
        return hit[1]
    durations = []
    for name in names:
        if f"_{skill}_" not in name:
            continue
        try:
            doc = store.read_json(f"_runs/{name}")
        except Exception:
            continue
        if doc.get("skill") == skill and doc.get("status") == "done" and isinstance(doc.get("duration_s"), (int, float)):
            durations.append(float(doc["duration_s"]))
    durations.sort()
    value = durations[len(durations) // 2] if durations else None
    _EXPECTED[key] = (len(names), value)
    return value


def helper(config: DomainConfig, case: Case, lang: str, store=None) -> HelperView | None:
    run = case.last_run
    if run is None or run.status not in ("queued", "running"):
        return None
    from ..domain.runs import policy_for
    phases = [PhaseView(key=str(ph.get("key")), word=str((ph.get("words") or {}).get(lang) or (ph.get("words") or {}).get("en") or ph.get("key")))
              for ph in policy_for(config, run.skill).get("phases") or [] if isinstance(ph, dict) and ph.get("key")]
    pr = run.progress or {}
    return HelperView(run=run.id, skill=run.skill, skill_word=config.word("skills", run.skill, lang, run.skill), status=run.status,
                      created=run.created, started=run.started or "", phases=phases, phase=min(int(pr.get("phase", -1)), len(phases) - 1),
                      now=str(pr.get("now") or ""), recent=[str(x) for x in pr.get("recent") or []][-6:], steps=int(pr.get("steps") or 0),
                      expected_s=expected_seconds(store, run.skill))


class AgainView(BaseModel):
    """A helper finished in this stage and the case did not move on: the viewer may send it again (SYS-161). An offer on
    the case, not a move — it never counts in anybody's stack."""
    skill: str
    skill_word: str
    finished: str = ""


def again(config: DomainConfig, case: Case, viewer: str | None, lang: str) -> AgainView | None:
    from ..domain.runs import may_order
    from ..domain.turn import stage_run
    last = stage_run(case)
    busy = case.last_run is not None and case.last_run.status in ("queued", "running")
    person = config.person(viewer) if viewer else None
    if last is None or last.status != "done" or busy or person is None or may_order(config, last.skill, person):
        return None
    return AgainView(skill=last.skill, skill_word=config.word("skills", last.skill, lang, last.skill), finished=last.finished or "")


def protocols(config: DomainConfig, case: Case, store, lang: str) -> list[dict]:
    """The gate protocols this case's stage asks for (an action that requires 'protocol:<id>'), each with its template's
    title, the actions it opens, and — once started — its items, answers and state (ADR-029). Protocols the case holds
    from earlier stages follow, read only."""
    from ..domain import protocol as gate
    st = config.stage(case.stage)
    wanted: dict[str, list[str]] = {}
    for a in (st.actions if st else []):
        for req in a.requires:
            if req.startswith("protocol:"):
                wanted.setdefault(req[9:], []).append(config.word("actions", a.label, lang, a.label))
    out = []
    for tid, opens in wanted.items():
        doc = (case.data or {}).get(f"protocol-{tid}.json")
        title = ""
        try:
            tpl = gate.load_template(config, getattr(store, "root", None), tid)
            title = (tpl.get("title") or {}).get(lang) or (tpl.get("title") or {}).get("en") or tid
        except gate.ProtocolError:
            title = tid
        out.append({"template": tid, "title": title, "opens": opens, "here": True, "doc": doc, "state": gate.state(doc) if doc else None})
    for base, doc in sorted((case.data or {}).items()):
        if base.startswith("protocol-") and isinstance(doc, dict) and doc.get("template") not in wanted:
            out.append({"template": doc.get("template"), "title": ((doc.get("title") or {}).get(lang) or doc.get("template")), "opens": [],
                        "here": False, "doc": doc, "state": gate.state(doc)})
    return out


class CaseView(CaseCard):
    meta: dict = Field(default_factory=dict)
    stations: list[StationView]
    slots: list[SlotView]
    entries: list[Entry]
    turns: list[Turn]
    my_turns: list[Turn]
    last_run: Run | None = None
    primary: str | None = None
    agent: str = "Claude"
    reopen_to: str = ""                                   # a closed case: the stage "Move back" (action `reopen`) returns it to; empty while it is in the work
    reopen_word: str = ""                                 # that stage in words
    held_by: list[str] = Field(default_factory=list)      # somebody else holds the case: their names; "Send a reminder" (action `remind`) goes to them
    take_back_to: str = ""                                # the viewer's own stage it came from: "Take it back" (action `take_back`) returns it there
    take_back_word: str = ""
    undo_step: str = ""                                   # the viewer's newest move, while nothing happened since: "Undo" (action `undo`) takes it back (ADR-025)
    undo_word: str = ""                                   # that move in words
    translations: dict[str, dict[str, str]] = Field(default_factory=dict)   # an original file → {language: the translation beside it}
    data: dict = Field(default_factory=dict)              # small JSON deliverables (a helper's reading, what was done), for the surface's cards
    waits: list[Dependency] = Field(default_factory=list) # the cases this one waits for, each found or not and closed or not (REQ-005 DP-02)
    released: bool = False                                # it waits, and all of it is closed: free to go on, but it does not move by itself (DP-03)
    helper: HelperView | None = None                      # a helper at work: phases, what it does now, how long it usually takes
    again: AgainView | None = None                        # a helper finished here, the case stayed: the viewer may send it again
    protocols: list[dict] = Field(default_factory=list)   # the gate protocols of this stage and earlier ones (ADR-029)


class ListEntryView(BaseModel):
    key: str
    word: str                                             # in the viewer's language
    words: dict = Field(default_factory=dict)             # every language, for the form that changes it
    color: str = ""
    description: str = ""
    status: str                                           # planned | active | retired
    cases: int = 0                                        # how many cases carry it (only on /api/lists)


class ListView(BaseModel):
    id: str
    word: str
    words: dict = Field(default_factory=dict)
    field: str                                            # the meta key the list fills
    on_create: bool = False                               # a new case asks for it
    entries: list[ListEntryView] = []


class FacetValue(BaseModel):
    key: str
    word: str
    color: str = ""


class FacetView(BaseModel):
    key: str                                              # the meta field (or "data_point")
    word: str
    kind: str                                             # list | person | date | text | point
    filter: bool = False
    sort: bool = False
    card: bool = False
    values: list[FacetValue] = []


class ConfigView(BaseModel):
    product: str
    lang: str
    stations: list[StationView]
    groups: list[GroupView]
    people: list[PersonView]
    theme: dict
    words: dict                                           # the vocabulary for the language, flat
    videos: list[dict] = []                               # explainers for this language: key, where, title, url, poster, seconds
    lists: list[ListView] = []                            # the value lists (SYS-105), words in this language
    facets: list[FacetView] = []                          # what the surface filters by, sorts by and shows on a card (domain/facets.py)


def by_word(config: DomainConfig, by: str, lang: str) -> str:
    """'role:assessor' → the role's word; a skill name or 'claude' → the agent's name; 'human' → nothing."""
    if not by or by == "human":
        return ""
    if by.startswith("role:"):
        return config.word("roles", by[5:], lang, by[5:])
    if by == "claude" or by in (config.run_policy.get("skills") or {}) or by in ("interpret", "derive", "reconcile", "asset"):
        agent = config.agent
        return agent.name if agent else by
    p = config.person(by)
    return p.name if p else by


def station_of(config: DomainConfig, stage: str) -> tuple[str, int]:
    st = config.stage(stage)
    key = st.key if st else "out"
    stations = config.stations
    return key, stations.index(key) if key in stations else len(stations) - 1


def group_of(config: DomainConfig, case: Case, main: Turn | None, viewer: str | None) -> str:
    """Where the surface lists a case: the viewer's move first, then Claude's, then the stage's own group."""
    if main and viewer and (main.actor == viewer or config.may_act(viewer, main.actor)):
        return "you"
    if main and main.actor == "claude":
        return "claude"
    st = config.stage(case.stage)
    g = st.group if st else "out"
    return "others" if g == "you" else g


def card(config: DomainConfig, case: Case, viewer: str | None, lang: str, seen: dict[str, str] | None = None, store=None) -> CaseCard:
    turns = whose.enrich(case, whose.turn(case, config, lang), config, lang)
    main = turns[0] if turns else None
    key, idx = station_of(config, case.stage)
    g = group_of(config, case, main, viewer)
    ext = str(case.meta.get("external_id") or case.meta.get("claim_number") or "")
    tpl = str(config.theme.get("external_url") or "")
    tint = value_lists.tint(config.lists, config.theme, case.meta)
    party = next((str(case.meta.get(k)).split(",")[0].strip() for k in ("reported_by", "customer", "client", "from_name", "from") if case.meta.get(k)), "")
    point = _point(store, case.id)
    return CaseCard(id=case.id, party=party, number=str(case.meta.get("number") or ""), tint=tint, title=str(localized(case.meta, lang).get("title") or case.meta.get("working_title") or case.id), label=case.label,
                    external_id=ext, external_url=(tpl.replace("{external_id}", ext) if ext and tpl else ""),
                    label_word=value_lists.value_word(config.lists, "label", case.label, lang, config.word("labels", case.label, lang, case.label)), stage=case.stage,
                    stage_word=config.word("stages", case.stage, lang, case.stage), station=key, station_index=idx, group=g,
                    group_word=config.word("groups", g, lang, g), since=case.since, date=str(case.meta.get("publishDate") or "")[:10],
                    turn=main, mine=bool(main and viewer and (main.actor == viewer or config.may_act(viewer, main.actor))),
                    unread=reads.unread(config, case, viewer, seen) if seen is not None else False,
                    data_point=(point.label or point.name) if point else "",
                    values=facets.values_of(case, facets.keys(config), point.name if point else ""))


def _point(store, case_id: str):
    return store.point_of(case_id) if store is not None and hasattr(store, "point_of") else None


def view(config: DomainConfig, case: Case, viewer: str | None, lang: str, file_url, seen: dict[str, str] | None = None, store=None) -> CaseView:
    c = card(config, case, viewer, lang, seen, store)
    turns = whose.enrich(case, whose.turn(case, config, lang), config, lang)
    mine = [t for t in turns if viewer and (t.actor == viewer or config.may_act(viewer, t.actor))]
    stations = [StationView(key=k, word=config.word("stations", k, lang, k), state="done" if i < c.station_index else "current" if i == c.station_index else "todo")
                for i, k in enumerate(config.stations)]
    slots = [SlotView(file=s.file, word=config.word("files", s.file, lang, s.file), shape=s.shape, required=s.required,
                      due_station=station_of(config, s.due_stage)[0] if s.due_stage else "", by=s.by, by_word=by_word(config, s.by, lang),
                      versions=[VersionView(name=v.name, version=v.version, size=v.size, url=file_url(case, v.name)) for v in s.versions], present=s.present)
             for s in case.slots]
    agent = config.agent
    back = stepping.reopen_target(config, case) or ""
    if back and not stepping.may_reopen(config, viewer, back):
        back = ""                                          # offered only to whom it is allowed (review S4)
    held = [p.name for p in stepping.holders(config, case, viewer)] if viewer else []
    pull = stepping.take_back_target(config, case, viewer) or ""
    undo = stepping.undoable(store, config, case, viewer) if store is not None else None
    undo_action = config.action(undo.from_, undo.action) if undo else None
    deps = depends.waits(case.meta, depends.resolver_for(store, config), lang) if store is not None else []
    return CaseView(**c.model_dump(), waits=deps, released=depends.released(deps), reopen_to=back, reopen_word=config.word("stages", back, lang, back) if back else "",
                    held_by=held, take_back_to=pull, take_back_word=config.word("stages", pull, lang, pull) if pull else "",
                    translations=translations(case.files), undo_step=undo.step_id if undo else "", undo_word=config.word("actions", undo_action.label if undo_action else undo.action, lang, undo.action) if undo else "",
                    meta={k: v for k, v in localized(case.meta, lang).items() if k != "entries"}, stations=stations, slots=slots, entries=names_in(config, with_actors(config, entries_in(case.entries, localized(case.meta, lang).get("entries"))), lang), turns=turns, my_turns=mine,
                    last_run=case.last_run, primary=config.primary(case.label), agent=agent.name if agent else "Claude",
                    helper=helper(config, case, lang, store),
                    again=again(config, case, viewer, lang),
                    protocols=protocols(config, case, store, lang),
                    data={k: localized(v, lang) for k, v in case.data.items() if k.endswith(".json") and not k.startswith(("gespraech", "nachfragen"))})


def list_views(config: DomainConfig, lang: str, counts: dict | None = None) -> list[ListView]:
    out = []
    for lst in config.lists.values():
        n = (counts or {}).get(lst["id"], {})
        out.append(ListView(id=lst["id"], word=value_lists.list_word(lst, lang, config.vocabulary), words=lst["word"], field=lst["field"], on_create=lst["on_create"],
                            entries=[ListEntryView(key=e["key"], word=value_lists.in_lang(e["word"], lang, e["key"]), words=e["word"], color=e["color"],
                                                   description=value_lists.in_lang(e["description"], lang), status=e["status"], cases=n.get(e["key"], 0))
                                     for e in lst["entries"]]))
    return out


def config_view(config: DomainConfig, lang: str, points: list | None = None) -> ConfigView:
    v = config.vocabulary.get(lang) or config.vocabulary.get("en") or {}
    groups_order = ["you", "claude", "others", "date", "planned", "out", "ideas", "archive"]
    return ConfigView(product=str(v.get("product") or config.name),
                      lang=lang, stations=[StationView(key=k, word=config.word("stations", k, lang, k), state="todo") for k in config.stations],
                      groups=[GroupView(key=g, word=config.word("groups", g, lang, g)) for g in groups_order],
                      people=[PersonView(id=p.id, name=p.name, kind=p.kind, roles=p.roles) for p in config.people],
                      theme=config.theme, words=v, lists=list_views(config, lang),
                      facets=[FacetView(**f) for f in facets.facets(config, lang, points)],
                      videos=[{"key": x["key"], "where": list(x.get("where", [])), "title": (x.get("title") or {}).get(lang) or (x.get("title") or {}).get("en") or x["key"],
                               "url": f"/api/videos/{x['file']}", "poster": f"/api/videos/{x['poster']}" if x.get("poster") else "", "seconds": int(x.get("seconds", 0))}
                              for x in config.videos if not x.get("lang") or x.get("lang") == lang] or
                             [{"key": x["key"], "where": list(x.get("where", [])), "title": (x.get("title") or {}).get(lang) or x["key"], "url": f"/api/videos/{x['file']}",
                               "poster": f"/api/videos/{x['poster']}" if x.get("poster") else "", "seconds": int(x.get("seconds", 0))} for x in config.videos])
