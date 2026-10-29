"""What the surface receives: cards, the case view, the configuration in words. Built from the domain, never from the folder directly."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..config import DomainConfig
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


class StationView(BaseModel):
    key: str
    word: str
    state: str                                            # done | current | todo


class GroupView(BaseModel):
    key: str
    word: str


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
    data: dict = Field(default_factory=dict)              # small JSON deliverables (a helper's reading, what was done), for the surface's cards


class ConfigView(BaseModel):
    product: str
    lang: str
    stations: list[StationView]
    groups: list[GroupView]
    people: list[PersonView]
    theme: dict
    words: dict                                           # the vocabulary for the language, flat
    videos: list[dict] = []                               # explainers for this language: key, where, title, url, poster, seconds
    order: list[str] = []                                 # the stack's rule (ADR-024): which kinds of move come first, `order` in stages.json or the default


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


def card(config: DomainConfig, case: Case, viewer: str | None, lang: str) -> CaseCard:
    turns = whose.enrich(case, whose.turn(case, config, lang), config, lang)
    main = turns[0] if turns else None
    key, idx = station_of(config, case.stage)
    g = group_of(config, case, main, viewer)
    ext = str(case.meta.get("external_id") or case.meta.get("claim_number") or "")
    tpl = str(config.theme.get("external_url") or "")
    covers = config.theme.get("covers") or {}
    tint = str((covers.get("colors") or {}).get(str(case.meta.get(covers.get("by") or "label") or ""), covers.get("fallback") or "")) if covers else ""
    return CaseCard(id=case.id, number=str(case.meta.get("number") or ""), tint=tint, title=str(case.meta.get("title") or case.meta.get("working_title") or case.id), label=case.label,
                    external_id=ext, external_url=(tpl.replace("{external_id}", ext) if ext and tpl else ""),
                    label_word=config.word("labels", case.label, lang, case.label), stage=case.stage,
                    stage_word=config.word("stages", case.stage, lang, case.stage), station=key, station_index=idx, group=g,
                    group_word=config.word("groups", g, lang, g), since=case.since, date=str(case.meta.get("publishDate") or "")[:10],
                    turn=main, mine=bool(main and viewer and (main.actor == viewer or config.may_act(viewer, main.actor))))


def view(config: DomainConfig, case: Case, viewer: str | None, lang: str, file_url) -> CaseView:
    c = card(config, case, viewer, lang)
    turns = whose.enrich(case, whose.turn(case, config, lang), config, lang)
    mine = [t for t in turns if viewer and (t.actor == viewer or config.may_act(viewer, t.actor))]
    mine.sort(key=lambda t: whose.rank(config, case, t))     # the gate shows the move the stack ranks first, not the engine's first
    stations = [StationView(key=k, word=config.word("stations", k, lang, k), state="done" if i < c.station_index else "current" if i == c.station_index else "todo")
                for i, k in enumerate(config.stations)]
    slots = [SlotView(file=s.file, word=config.word("files", s.file, lang, s.file), shape=s.shape, required=s.required,
                      due_station=station_of(config, s.due_stage)[0] if s.due_stage else "", by=s.by, by_word=by_word(config, s.by, lang),
                      versions=[VersionView(name=v.name, version=v.version, size=v.size, url=file_url(case, v.name)) for v in s.versions], present=s.present)
             for s in case.slots]
    agent = config.agent
    return CaseView(**c.model_dump(), meta=case.meta, stations=stations, slots=slots, entries=case.entries, turns=turns, my_turns=mine,
                    last_run=case.last_run, primary=config.primary(case.label), agent=agent.name if agent else "Claude",
                    data={k: v for k, v in case.data.items() if k.endswith(".json") and not k.startswith(("gespraech", "nachfragen"))})


def config_view(config: DomainConfig, lang: str) -> ConfigView:
    v = config.vocabulary.get(lang) or config.vocabulary.get("en") or {}
    groups_order = ["you", "claude", "others", "date", "planned", "out", "ideas", "archive"]
    return ConfigView(product=str(v.get("product") or config.name),
                      lang=lang, stations=[StationView(key=k, word=config.word("stations", k, lang, k), state="todo") for k in config.stations],
                      groups=[GroupView(key=g, word=config.word("groups", g, lang, g)) for g in groups_order],
                      people=[PersonView(id=p.id, name=p.name, kind=p.kind, roles=p.roles) for p in config.people],
                      theme=config.theme, words=v, order=list(config.order or whose.ORDER),
                      videos=[{"key": x["key"], "where": list(x.get("where", [])), "title": (x.get("title") or {}).get(lang) or (x.get("title") or {}).get("en") or x["key"],
                               "url": f"/api/videos/{x['file']}", "poster": f"/api/videos/{x['poster']}" if x.get("poster") else "", "seconds": int(x.get("seconds", 0))}
                              for x in config.videos if not x.get("lang") or x.get("lang") == lang] or
                             [{"key": x["key"], "where": list(x.get("where", [])), "title": (x.get("title") or {}).get(lang) or x["key"], "url": f"/api/videos/{x['file']}",
                               "poster": f"/api/videos/{x['poster']}" if x.get("poster") else "", "seconds": int(x.get("seconds", 0))} for x in config.videos])
