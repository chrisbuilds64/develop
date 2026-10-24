"""Agents: who one may work with in a workspace — identity, memory, skills and rights in one directory.

A workspace's `agents` component is a directory with one folder per agent:

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
allows: an agent never does more than the skill, a skill never more than the agent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
ENGINES = ("claude-code",)                     # the one engine the runner can drive today; `openai` would be the next
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
    model: str | None = None
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

    @property
    def signature_path(self) -> Path | None:
        return self.dir / self.signature if self.signature else None

    @property
    def avatar_path(self) -> Path | None:
        p = self.dir / self.avatar if self.avatar else None
        return p if p and p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") else None

    @property
    def initials(self) -> str:
        return "".join(w[0] for w in self.label.split()[:2]).upper() or self.id[:2].upper()

    @property
    def notes_path(self) -> Path | None:
        return self.dir / self.notes if self.notes else None

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
        if skill_rules is None:
            return mine
        out = dict(skill_rules)
        out["tools"] = [t for t in skill_rules.get("tools", []) if t in self.tools]
        out["web"] = bool(skill_rules.get("web")) and self.web
        out["write"] = [w for w in skill_rules.get("write", []) if w in self.write]
        out["agent"] = self.label
        if self.model and not skill_rules.get("model"):
            out["model"] = self.model
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
        engine=engine, model=raw.get("model"), signature=raw.get("signature", f"{aid}-signature.md"),
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
