"""Sessions: one person with one of their agents, on one topic, at a place — started and ended by a button.

The keyboard has /session-start and /session-end; this is the same lifecycle for the cockpit. A session is
bound to an agent because an agent is an identity, and a change of identity is a new session (agent registry).
It belongs to the person and the agent, not to a workspace (ADR-020): the place where it was opened — workspace,
application, item — travels with it as context. The person's account holds the store, per stage, one file per
thing, so two sessions never write the same file:

    active/<id>.json      the lease and the record while it runs: who, which agent, topic, the Claude session
    turns/<id>.jsonl      the conversation, one line per message
    queue/<order>.json    what the runner is to do next: a message (`chat`) or the closing turn (`end`)
    closed/<id>.json      the record after the end; the newest one of an agent points at the log it starts from

The log itself — `<date>_<topic>.md`, written by the agent at the end — goes to the person's own folder (`log_dir`),
which they choose on their account; without one it stays beside the store under logs/.

Parallel sessions are normal. The same agent, person and topic twice is reported as a conflict when
the second starts — a warning, not a refusal, like the lease table at the keyboard. One message at a time per
session: the conversation is a chain of `--resume`, and a second order before the first is answered would fork it.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

SLUG = re.compile(r"[^a-z0-9]+")
ID = re.compile(r"^\d{8}-\d{6}_[a-z][a-z0-9_-]{0,31}_[a-z0-9-]{1,48}$")
KINDS = ("chat", "end")
MAX_TEXT = 20000


class SessionError(Exception):
    """A sentence for the person, never a stack trace."""


def _now() -> dt.datetime:
    return dt.datetime.now().astimezone()


def slug(text: str) -> str:
    s = SLUG.sub("-", text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")).strip("-")
    return s[:48].strip("-") or "session"


@dataclass
class Session:
    id: str
    agent: str
    user: str
    topic: str
    started: str
    status: str = "active"                     # active → ending → closed
    claude_session: str | None = None          # set by the runner after the first answer; every later turn resumes it
    turns: int = 0
    ended: str | None = None
    log: str | None = None                     # the written log, an absolute path in the person's folder
    starts_from: str | None = None             # the log of this agent's previous session
    place: dict = field(default_factory=dict)  # where it was opened: {"workspace", "application", "item", "url"}
    focus: dict = field(default_factory=dict)  # the case the agent last had laid before it (the runner keeps this)

    @property
    def workspace(self) -> str | None:
        return self.place.get("workspace")

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.agent, self.user, slug(self.topic))


PLACE_KEYS = ("workspace", "application", "item", "url", "title", "case", "stage", "label", "view", "document", "help")


def clean_place(place: dict | None) -> dict:
    """Only the known keys, as short strings — the place is context the browser reports, not something to trust."""
    return {k: str(v)[:300] for k, v in (place or {}).items() if k in PLACE_KEYS and v}


@dataclass
class Store:
    dir: Path
    log_dir: Path | None = None                # the person's own folder for logs; None = logs/ beside the store

    # ---------------------------------------------------------------- paths
    def _p(self, *parts: str) -> Path:
        return self.dir.joinpath(*parts)

    def _check_id(self, sid: str) -> str:
        if not ID.match(sid):
            raise SessionError(f"'{sid}' is not a session id")
        return sid

    def _write(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)

    def _read(self, path: Path) -> Session:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if "workspace" in raw:                         # a record from ADR-019, when sessions lived in a workspace
            raw.setdefault("place", {})["workspace"] = raw.pop("workspace")
        if raw.get("log") and not Path(raw["log"]).is_absolute():
            raw["log"] = str(self.dir / raw["log"])
        if raw.get("starts_from") and not Path(raw["starts_from"]).is_absolute():
            raw["starts_from"] = str(self.dir / raw["starts_from"])
        return Session(**{k: v for k, v in raw.items() if k in Session.__dataclass_fields__})

    # ---------------------------------------------------------------- reading
    def active(self, user: str | None = None) -> list[Session]:
        d = self._p("active")
        out = [self._read(f) for f in sorted(d.glob("*.json"))] if d.is_dir() else []
        return [s for s in out if user is None or s.user == user]

    def closed(self, agent: str | None = None) -> list[Session]:
        d = self._p("closed")
        out = [self._read(f) for f in sorted(d.glob("*.json"))] if d.is_dir() else []
        return [s for s in out if agent is None or s.agent == agent]

    def get(self, sid: str) -> Session | None:
        self._check_id(sid)
        for where in ("active", "closed"):
            p = self._p(where, f"{sid}.json")
            if p.is_file():
                return self._read(p)
        return None

    def latest_log(self, agent: str) -> Path | None:
        """The log this agent's next session starts from: the newest closed session of the agent that left one."""
        for s in reversed(self.closed(agent)):
            if s.log and Path(s.log).is_file():
                return Path(s.log)
        return None

    def transcript(self, sid: str) -> list[dict]:
        p = self._p("turns", f"{self._check_id(sid)}.jsonl")
        if not p.is_file():
            return []
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    def pending(self, sid: str) -> dict | None:
        """The order of this session the runner has not finished yet, if any."""
        d = self._p("queue")
        if not d.is_dir():
            return None
        for f in sorted(d.glob("*.json")):
            o = json.loads(f.read_text(encoding="utf-8"))
            if o.get("session") == sid and o.get("status") in ("queued", "running"):
                return o
        return None

    # ---------------------------------------------------------------- lifecycle
    def start(self, agent: str, user: str, topic: str, place: dict | None = None) -> tuple[Session, list[Session]]:
        """A new session and its lease. Returns it and the active sessions it overlaps with (same key)."""
        topic = " ".join(topic.split())[:120]
        if not topic:
            raise SessionError("a session needs a topic — one line on what it is about")
        now = _now()
        sid = f"{now.strftime('%Y%m%d-%H%M%S')}_{agent}_{slug(topic)}"
        if self._p("active", f"{sid}.json").exists():
            raise SessionError("a session with this id started this very second — try again")
        prev = self.latest_log(agent)
        s = Session(id=sid, agent=agent, user=user, topic=topic, started=now.isoformat(timespec="seconds"),
                    starts_from=str(prev) if prev else None, place=clean_place(place))
        overlapping = [o for o in self.active() if o.key == s.key]
        self._write(self._p("active", f"{sid}.json"), asdict(s))
        return s, overlapping

    def _order(self, s: Session, kind: str, text: str, focus: dict | None = None) -> dict:
        if kind not in KINDS:
            raise SessionError(f"'{kind}' is not an order kind")
        now = _now()
        order = {"id": f"{now.strftime('%Y%m%d-%H%M%S-%f')}_{kind}_{s.id}", "type": kind, "session": s.id,
                 "place": s.place, "agent": s.agent, "requested_by": s.user, "runner": "claude-code",
                 "status": "queued", "created": now.isoformat(timespec="seconds"), "text": text, "focus": focus or {}}
        self._write(self._p("queue", f"{order['id']}.json"), order)
        return order

    def _mine(self, sid: str, user: str) -> Session:
        s = self.get(sid)
        if s is None or s.status == "closed":
            raise SessionError("this session is not running")
        if s.user != user:
            raise SessionError("this session belongs to someone else")
        return s

    def say(self, sid: str, user: str, text: str, focus: dict | None = None) -> dict:
        """One message into the session. The runner answers it; the page shows the answer when it is there.
        `focus` is what the person has open at the moment they send — the case the question is about."""
        s = self._mine(sid, user)
        text = text.strip()
        if not text:
            raise SessionError("an empty message")
        if len(text) > MAX_TEXT:
            raise SessionError(f"a message of more than {MAX_TEXT} characters — put the material into a file")
        if s.status != "active":
            raise SessionError("this session is ending — no more messages")
        if self.pending(sid):
            raise SessionError("the agent is still answering the last message")
        focus = clean_place(focus)
        self.add_turn(sid, "user", text, by=user, focus=focus.get("case"))
        order = self._order(s, "chat", text, focus)
        return order

    def end(self, sid: str, user: str, note: str = "") -> dict:
        """The closing turn: the agent writes the session log; the runner releases the lease after it."""
        s = self._mine(sid, user)
        if s.status != "active":
            raise SessionError("this session is already ending")
        if self.pending(sid):
            raise SessionError("the agent is still answering — end the session when the answer is there")
        s.status = "ending"
        self._write(self._p("active", f"{sid}.json"), asdict(s))
        return self._order(s, "end", note.strip())

    # ---------------------------------------------------------------- the runner's side
    def add_turn(self, sid: str, role: str, text: str, **meta) -> None:
        p = self._p("turns", f"{self._check_id(sid)}.jsonl")
        p.parent.mkdir(parents=True, exist_ok=True)
        line = {"at": _now().isoformat(timespec="seconds"), "role": role, "text": text, **{k: v for k, v in meta.items() if v is not None}}
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")

    def update(self, sid: str, **fields) -> Session:
        p = self._p("active", f"{self._check_id(sid)}.json")
        if not p.is_file():
            raise SessionError(f"session {sid} is not active")
        s = self._read(p)
        for k, v in fields.items():
            setattr(s, k, v)
        self._write(p, asdict(s))
        return s

    def log_path(self, s: Session) -> Path:
        """Where the closing turn writes the log: <log_dir>/<date>_<topic>.md, a suffix when the name is taken."""
        d = self.log_dir or self._p("logs")
        base = f"{s.started[:10]}_{slug(s.topic)}"
        p = d / f"{base}.md"
        n = 2
        while p.exists():
            p = d / f"{base}-{n}.md"
            n += 1
        return p

    def close(self, sid: str, log: Path | None) -> Session:
        """The lease is released: the record moves to closed/, with the log the next session starts from."""
        p = self._p("active", f"{self._check_id(sid)}.json")
        s = self._read(p)
        s.status, s.ended = "closed", _now().isoformat(timespec="seconds")
        s.log = str(log) if log and log.is_file() else None
        self._write(self._p("closed", f"{sid}.json"), asdict(s))
        os.remove(p)
        return s
