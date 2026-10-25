"""Agents: the organisation's job profiles (templates) and the person's team (hired agents) — ADR-020.

The organisation keeps templates, one folder each (today `control/shared-context/agents/`):

    <agents>/<id>/agent.json            the definition: what the agent is, may run, may touch, and who may choose it
    <agents>/<id>/<id>-signature.md     its operating identity (the file name agent.json names)
    <agents>/<id>/working-notes.md      what it has learned — its own memory, beside the general context

`agent.json`:

    {"id": "axel", "label": "Axel", "role": "Executor, implementer", "engine": "claude-code", "model": "…",
     "signature": "axel-signature.md", "notes": "working-notes.md", "context": "axel",
     "skills": ["interpret"], "tools": ["Read", "Grep", "Glob"], "web": false, "write": [],
     "users": [], "roles": []}

What is missing is not allowed: no `skills`, no orders; no `tools`, a read-only conversation. A folder without
agent.json is no agent, even with a signature in it: the same directory holds the signatures of the humans
(Chris, Akhil) and of instances that run elsewhere (Atlas on GPT), and none of them is someone to chat with
here until a definition says so.

Rights are an intersection. An order gets what run-policy.json grants the skill *and* what the agent's ceiling
allows: an agent never does more than the skill, a skill never more than the agent. The template's `users` and
`roles` say who may hire it.

A person hires agents into their account — `<accounts>/<name>/agents/<id>/agent.json`:

    {"template": "atlas", "hired": "2026-10-25", "model": "…", "memory": "/home/runner/envs/{stage}/notes/shared-context/agents/atlas"}

The hired agent takes identity and avatar from the template's folder and keeps its own memory: working notes in
`memory` ({stage} allowed), by default its folder in the account. It may be narrower than its template (tools,
skills, web), never wider; model and engine may differ. Two people's Atlas share the role, not the memory.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field, replace
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
ENGINES = ("claude-code", "codex", "openai")   # claude-code / codex: a session with tools on the person's subscription; openai: API, conversation only
READ_ONLY = ("Read", "Grep", "Glob")


class AgentError(Exception):
    """A sentence for the person, never a stack trace."""


@dataclass(frozen=True)
class Agent:
    id: str
    label: str
    dir: Path
    role: str = ""
    engine: str = "claude-code"
    model: str | None = None                   # the model assigned to this agent; without one, the stage's default
    fallback_model: str | None = None          # taken when the assigned one is overloaded or not available
    signature: str | None = None
    notes: str | None = None
    avatar: str | None = None                  # an image in the agent's folder; without one the page shows initials
    context: str | None = None                 # the instance in context-manifest.json whose general context it loads
    skills: tuple[str, ...] = ()
    tools: tuple[str, ...] = READ_ONLY
    web: bool = False
    write: tuple[str, ...] = ()
    users: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    memory_dir: Path | None = None             # where its working notes live; None = its own folder
    template: str | None = None                # the job profile it was hired from

    @property
    def signature_path(self) -> Path | None:
        return self.dir / self.signature if self.signature else None

    @property
    def avatar_path(self) -> Path | None:
        p = self.dir / self.avatar if self.avatar else None
        return p if p and p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") else None

    def thumbnail(self, cache: Path, size: int = 128) -> Path | None:
        """The avatar at `size` pixels as WebP, made once and kept in `cache` — the originals are photographs of
        several megabytes, shown at 22 to 44 pixels. Keyed by the original's mtime, so a new picture is picked up."""
        src = self.avatar_path
        if src is None:
            return None
        out = cache / f"{self.id}-{src.stat().st_mtime_ns}-{size}.webp"
        if out.is_file():
            return out
        from PIL import Image
        cache.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = im.convert("RGB")
            side = min(im.size)                          # square from the centre, then down to size
            left, top = (im.width - side) // 2, (im.height - side) // 2
            im = im.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
            tmp = out.with_suffix(".tmp")
            im.save(tmp, "WEBP", quality=82, method=6)
            tmp.replace(out)
        for old in cache.glob(f"{self.id}-*-{size}.webp"):
            if old != out:
                old.unlink(missing_ok=True)
        return out

    @property
    def initials(self) -> str:
        return "".join(w[0] for w in self.label.split()[:2]).upper() or self.id[:2].upper()

    @property
    def notes_path(self) -> Path | None:
        return (self.memory_dir or self.dir) / self.notes if self.notes else None

    def may_be_chosen_by(self, user: str | None, role: str | None) -> bool:
        if not self.users and not self.roles:
            return True
        return (user is not None and user in self.users) or (role is not None and role in self.roles)

    def may_run(self, skill: str) -> bool:
        return skill in self.skills

    def rules_for(self, skill_rules: dict | None = None) -> dict:
        """The rights of one session: the skill's rules from run-policy.json cut down to this agent's ceiling.
        Without skill rules (a conversation) the ceiling is the rule. Never wider than either side."""
        mine = {"tools": list(self.tools), "web": self.web, "write": list(self.write), "agent": self.label}
        if self.model:
            mine["model"] = self.model
        if self.fallback_model:
            mine["fallback_model"] = self.fallback_model
        if skill_rules is None:
            return mine
        out = dict(skill_rules)
        out["tools"] = [t for t in skill_rules.get("tools", []) if t in self.tools]
        out["web"] = bool(skill_rules.get("web")) and self.web
        out["write"] = [w for w in skill_rules.get("write", []) if w in self.write]
        out["agent"] = self.label
        if self.model and not skill_rules.get("model"):
            out["model"] = self.model
        if self.fallback_model:
            out["fallback_model"] = self.fallback_model
        return out

    def summary(self) -> dict:
        return {"id": self.id, "label": self.label, "role": self.role, "engine": self.engine, "model": self.model,
                "skills": list(self.skills), "tools": list(self.tools), "web": self.web,
                "signature": bool(self.signature_path and self.signature_path.is_file()),
                "notes": bool(self.notes_path and self.notes_path.is_file())}


def _tuple(raw, where: str, key: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(x, str) for x in raw):
        raise AgentError(f"{where}: '{key}' must be a list of names")
    return tuple(raw)


def load_agent(folder: Path) -> Agent | None:
    """One agent from its folder; None when the folder carries no agent.json."""
    aid = folder.name
    spec = folder / "agent.json"
    if not NAME.match(aid) or not spec.is_file():
        return None
    try:
        raw = json.loads(spec.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise AgentError(f"{spec} is not valid JSON: {exc}") from exc
    where = f"agent '{aid}'"
    if raw.get("id", aid) != aid:
        raise AgentError(f"{where}: id '{raw.get('id')}' differs from its folder name")
    engine = raw.get("engine", "claude-code")
    if engine not in ENGINES:
        raise AgentError(f"{where}: engine '{engine}' — the runner drives {', '.join(ENGINES)}")
    for key in ("signature", "notes", "avatar"):
        name = raw.get(key)
        if name and ("/" in name or name.startswith(".")):
            raise AgentError(f"{where}: '{key}' is a file name inside the agent's folder, not a path")
    return Agent(
        id=aid, label=str(raw.get("label") or aid.capitalize()), dir=folder, role=str(raw.get("role", "")),
        engine=engine, model=raw.get("model"), fallback_model=raw.get("fallback_model"), signature=raw.get("signature", f"{aid}-signature.md"),
        notes=raw.get("notes", "working-notes.md"), context=raw.get("context", aid),
        avatar=raw.get("avatar", f"{aid}-avatar.png"),
        skills=_tuple(raw.get("skills"), where, "skills"),
        tools=_tuple(raw.get("tools"), where, "tools") if "tools" in raw else READ_ONLY,
        web=bool(raw.get("web", False)), write=_tuple(raw.get("write"), where, "write"),
        users=_tuple(raw.get("users"), where, "users"), roles=_tuple(raw.get("roles"), where, "roles"),
    )


@dataclass
class Catalog:
    """The agents of one directory. Broken definitions are reported, not fatal: one bad folder keeps the rest."""
    dir: Path | None
    agents: dict[str, Agent] = field(default_factory=dict)
    problems: dict[str, str] = field(default_factory=dict)

    @classmethod
    def load(cls, directory: Path | None) -> "Catalog":
        cat = cls(dir=directory)
        if directory is None or not directory.is_dir():
            return cat
        for folder in sorted(p for p in directory.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
            try:
                a = load_agent(folder)
            except AgentError as exc:
                cat.problems[folder.name] = str(exc)
                continue
            if a is not None:
                cat.agents[a.id] = a
        return cat

    def get(self, aid: str) -> Agent | None:
        return self.agents.get(aid)

    def for_user(self, user: str | None, role: str | None) -> list[Agent]:
        return [a for a in self.agents.values() if a.may_be_chosen_by(user, role)]


# -------------------------------------------------------------------- the person's team (ADR-020)

NARROW = ("tools", "skills", "write")           # a hired agent may keep fewer of these than its template, never more
OVERRIDE = ("label", "model", "fallback_model", "engine")


class Team:
    """One person's hired agents, resolved against the organisation's templates, for one stage."""

    def __init__(self, accounts_root: Path, user: str, templates: Catalog, stage: str = "local"):
        if not NAME.match(user or ""):
            raise AgentError(f"'{user}' is not an account name")
        self.dir = Path(accounts_root) / user / "agents"
        self.user, self.templates, self.stage = user, templates, stage or "local"
        self.agents: dict[str, Agent] = {}
        self.problems: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        self.agents, self.problems = {}, {}
        if not self.dir.is_dir():
            return
        for folder in sorted(p for p in self.dir.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
            try:
                a = self._resolve(folder)
            except AgentError as exc:
                self.problems[folder.name] = str(exc)
                continue
            if a is not None:
                self.agents[a.id] = a

    def _resolve(self, folder: Path) -> Agent | None:
        spec = folder / "agent.json"
        if not NAME.match(folder.name) or not spec.is_file():
            return None
        try:
            raw = json.loads(spec.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise AgentError(f"{spec} is not valid JSON: {exc}") from exc
        tid = raw.get("template")
        if not tid:                                       # a definition of the person's own, signature in their folder
            a = load_agent(folder)
            return replace(a, memory_dir=self._memory(raw, folder)) if a else None
        t = self.templates.get(tid)
        if t is None:
            raise AgentError(f"agent '{folder.name}': no template '{tid}' in the organisation")
        changes: dict = {"id": folder.name, "template": tid, "memory_dir": self._memory(raw, folder)}
        for key in OVERRIDE:
            if raw.get(key):
                changes[key] = str(raw[key])
        if changes.get("engine", t.engine) not in ENGINES:
            raise AgentError(f"agent '{folder.name}': engine '{changes['engine']}' — the runner drives {', '.join(ENGINES)}")
        for key in NARROW:
            if key in raw:
                mine = _tuple(raw[key], f"agent '{folder.name}'", key)
                wider = [x for x in mine if x not in getattr(t, key)]
                if wider:
                    raise AgentError(f"agent '{folder.name}': {key} {', '.join(wider)} — more than its template allows")
                changes[key] = mine
        if raw.get("web") is False:
            changes["web"] = False
        return replace(t, **changes)

    def _memory(self, raw: dict, folder: Path) -> Path:
        m = raw.get("memory")
        return Path(str(m).replace("{stage}", self.stage)).expanduser() if m else folder

    def get(self, aid: str) -> Agent | None:
        return self.agents.get(aid)

    def hireable(self, role: str | None) -> list[Agent]:
        return [t for t in self.templates.agents.values() if t.may_be_chosen_by(self.user, role)]

    def hire(self, template: str, aid: str | None = None, role: str | None = None, **settings) -> Agent:
        """A new member of the team from an organisation template. `settings`: label, model, fallback_model, engine,
        memory and narrower tools/skills/write — written into the hired agent's agent.json, checked on load."""
        t = self.templates.get(template)
        if t is None or not t.may_be_chosen_by(self.user, role):
            raise AgentError(f"'{template}' is not a profile you may hire")
        aid = aid or template
        if not NAME.match(aid):
            raise AgentError(f"'{aid}' is not an agent id — lower-case letters, digits, - and _")
        folder = self.dir / aid
        if (folder / "agent.json").exists():
            raise AgentError(f"you already have an agent '{aid}'")
        doc = {"$comment": f"Hired by {self.user} from the organisation's template '{template}' (ADR-020).",
               "template": template, "hired": dt.date.today().isoformat(),
               **{k: v for k, v in settings.items() if v not in (None, "", [])}}
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "agent.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.load()
        if aid not in self.agents:
            problem = self.problems.get(aid, "unknown")
            (folder / "agent.json").unlink()
            raise AgentError(problem)
        return self.agents[aid]

    def dismiss(self, aid: str) -> bool:
        """Leaves the team. The folder stays as `_dismissed-<id>-<date>` — memory is not thrown away by a click."""
        folder = self.dir / aid
        if not NAME.match(aid) or not (folder / "agent.json").is_file():
            return False
        folder.rename(self.dir / f"_dismissed-{aid}-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}")
        self.load()
        return True
