"""Domain configuration (ADR-015): stages, deliverables, words, people, theme — files, not code.

Two places feed it. The domain directory (`config/<domain>/`) carries `stages.json`, `theme.json` and
defaults for the rest. The pipeline root carries what the tools already keep there today —
`artifacts.json`, `vocabulary.json`, `people.json`, `calendar.json` — and wins where both exist, so a
running pipeline keeps its own words.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .models import Action, Deliverable, Person, Stage

ROOT_FILES = ("artifacts.json", "vocabulary.json", "people.json", "calendar.json", "run-policy.json")


def _merge(base: dict, over: dict) -> dict:
    """`over` wins key by key; nested tables merge, so a tree that names a few words keeps all the others."""
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _read(p: Path) -> dict | None:
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


@dataclass
class DomainConfig:
    name: str
    stages: list[Stage]
    artifacts: dict                               # the artifacts.json object as it is
    vocabulary: dict                              # {lang: {labels, stages, files, actions, …}}
    people: list[Person]
    calendar: dict = field(default_factory=dict)
    run_policy: dict = field(default_factory=dict)
    order: list = field(default_factory=list)     # the stack's rule, `order` in stages.json: which kinds of move come first (default: turn.ORDER)
    theme: dict = field(default_factory=dict)
    lang: str = "en"
    config_version: str = "1"
    dir: Path | None = None                       # where the domain files came from (replies for the demo live beside them)
    videos: list = field(default_factory=list)    # explainer videos (videos.json): key, where, title, file, poster, minutes

    # ------------------------------------------------------------------ loading
    @classmethod
    def load(cls, domain_dir: Path, root: Path | None = None) -> "DomainConfig":
        domain_dir = Path(domain_dir)
        stages_doc = _read(domain_dir / "stages.json") or {}
        theme = _read(domain_dir / "theme.json") or {}
        docs = {}
        for name in ROOT_FILES:
            doc = (_read(root / name) if root else None) or _read(domain_dir / name)
            docs[name] = doc or {}
        if root and _read(root / "vocabulary.json"):      # a tree's words add to the domain's, they do not erase the rest
            docs["vocabulary.json"] = _merge(_read(domain_dir / "vocabulary.json") or {}, docs["vocabulary.json"])
        people = [Person(**p) for p in docs["people.json"].get("people", [])]
        # A running pipeline's people.json may know the persons but not their roles (the PressRoom's did, 2026-10-24);
        # the domain's own people.json then lends the roles to the same ids, so the gates know whose move it is.
        own = _read(domain_dir / "people.json") or {}
        lent = {p["id"]: p.get("roles", []) for p in own.get("people", []) if isinstance(p, dict) and p.get("id")}
        for person in people:
            if not person.roles and lent.get(person.id):
                person.roles = list(lent[person.id])
        return cls(
            name=theme.get("name") or stages_doc.get("name") or domain_dir.name,
            stages=[Stage(**s) for s in stages_doc.get("stages", [])],
            artifacts=docs["artifacts.json"],
            vocabulary=docs["vocabulary.json"],
            people=people,
            calendar=docs["calendar.json"],
            run_policy=docs["run-policy.json"],
            theme=theme,
            lang=theme.get("lang") or stages_doc.get("lang") or "en",
            config_version=str(stages_doc.get("configVersion") or "1"),
            order=[str(k) for k in (stages_doc.get("order") or [])],
            dir=domain_dir,
            videos=[v for v in ((_read(domain_dir / "videos.json") or {}).get("videos") or []) if isinstance(v, dict) and v.get("key") and v.get("file")],
        )

    # ------------------------------------------------------------------ stages
    def stage(self, folder: str) -> Stage | None:
        return next((s for s in self.stages if s.folder == folder), None)

    def stage_by_key(self, key: str) -> Stage | None:
        return next((s for s in self.stages if s.key == key), None)

    @property
    def stations(self) -> list[str]:
        """The keys in order, duplicates folded — the line the surface draws."""
        out: list[str] = []
        for s in self.stages:
            if s.group != "archive" and s.key not in out:        # the archive is a place, not a station on the way
                out.append(s.key)
        return out

    def action(self, folder: str, action_id: str) -> Action | None:
        st = self.stage(folder)
        return next((a for a in st.actions if a.id == action_id), None) if st else None

    # ------------------------------------------------------------------ deliverables
    def deliverables(self, label: str) -> list[Deliverable]:
        """Every deliverable a case of this label collects, common ones first."""
        def norm(x) -> Deliverable:
            if isinstance(x, str):
                return Deliverable(file=x)
            return Deliverable(file=x["file"], stage=x.get("stage", ""), by=x.get("by", ""),
                               shape=x.get("shape") or self._shape_of(x["file"]), required=bool(x.get("required", False)),
                               collects=x.get("collects"))
        fmt = self.artifacts.get("formats", {}).get(label, {})
        return [norm(x) for x in self.artifacts.get("common", [])] + [norm(x) for x in fmt.get("artifacts", [])]

    def primary(self, label: str) -> str | None:
        return (self.artifacts.get("formats", {}).get(label) or {}).get("primary")

    @staticmethod
    def _shape_of(file: str) -> str:
        """A shape from the file name when the configuration does not say one."""
        stem, _, ext = file.rpartition(".")
        if ext in ("png", "jpg", "jpeg", "webp"):
            if "16x9" in stem:
                return "image-16x9"
            if "4x5" in stem:
                return "image-4x5"
            return "image"
        if ext in ("mp4", "mov", "webm"):
            return "video-9x16" if "9x16" in stem or "reel" in stem else "video"
        if ext == "pdf":
            return "pdf"
        return "text"

    # ------------------------------------------------------------------ words
    def word(self, kind: str, key: str, lang: str | None = None, fallback: str | None = None) -> str:
        v = self.vocabulary.get(lang or self.lang) or self.vocabulary.get("en") or {}
        section = v.get(kind)
        if not isinstance(section, dict):
            return fallback if fallback is not None else key
        return section.get(key) or (fallback if fallback is not None else key)

    # ------------------------------------------------------------------ people
    def person(self, ref: str | None) -> Person | None:
        """By id or name, case does not matter."""
        if not ref:
            return None
        r = ref.strip().lower()
        return next((p for p in self.people if r in (p.id.lower(), p.name.lower())), None)

    def persons_for(self, actor: str | None) -> list[Person]:
        """'role:approver' → everyone with that role (deputies included); 'person:x' or 'x' → that person; 'claude' → the agents."""
        if not actor:
            return []
        if actor == "claude":
            return [p for p in self.people if p.kind == "agent"]
        if actor.startswith("role:"):
            role = actor[5:]
            direct = [p for p in self.people if role in p.roles]
            deputies = [self.person(p.deputy) for p in direct if p.deputy]
            return direct + [d for d in deputies if d and d not in direct]
        ref = actor[7:] if actor.startswith("person:") else actor
        p = self.person(ref)
        return [p] if p else []

    def may_act(self, person_id: str, actor: str | None) -> bool:
        return any(p.id == person_id for p in self.persons_for(actor))

    @property
    def agent(self) -> Person | None:
        return next((p for p in self.people if p.kind == "agent"), None)
