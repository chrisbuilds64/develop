"""The replay runner: in the public demo, a helper's result is prepared and played back after a short delay (ADR-016).

It takes queued orders from `_runs/`, marks them running, waits, and then does what a real run would do:
write the prepared files into the case, append the agent's entry, move the case if the reply says so,
and mark the order done with a cost line. Replies live in `demo/replies/<skill>.json`:

    {"delay_s": 4, "files": {"abgleich.md": "replies/abgleich.md"}, "entry": {"title": "…", "text": "…"},
     "to": null, "cost_usd": 0.0, "model": "replay"}

A live run never happens here. The real runner (Claude Code headless) takes orders from a real pipeline.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
import time
from pathlib import Path

from ..config import DomainConfig
from ..domain import entries as thread
from ..domain.step import _append_entry
from ..store import FsStore, StoreError

HERE = Path(__file__).resolve().parent


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def load_reply(replies_dir: Path, skill: str, config: DomainConfig | None = None, root: Path | None = None, case_id: str | None = None,
               round_no: int = 0) -> tuple[dict | None, Path]:
    """Where a prepared reply comes from, nearest first: the world's own `_replies/` at the pipeline root — for this very case
    in this round (`<skill>.<case>.<n>.json`, a helper asked again answers again), for the case (`<skill>.<case>.json`), for its
    label (`<skill>.<LABEL>.json`) or for the skill — then the domain's `config/<domain>/replies/`, then the shared folder."""
    places: list[tuple[Path, str]] = []
    if root is not None:
        if case_id:
            if round_no:
                places.append((root / "_replies", f"{skill}.{case_id}.{round_no}.json"))
            places.append((root / "_replies", f"{skill}.{case_id}.json"))
            places.append((root / "_replies", f"{skill}.{case_id.split('-')[0]}.json"))   # per label: a case a hand-off opened has an id nobody could prepare
        places.append((root / "_replies", f"{skill}.json"))
    if config and config.dir:
        places.append((config.dir / "replies", f"{skill}.json"))
    if replies_dir is not None:
        places.append((replies_dir, f"{skill}.json"))
    for d, name in places:
        p = d / name
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")), d
    return None, replies_dir


def _round(store: FsStore, doc: dict) -> int:
    """Which time this helper is asked on this case: 1 + the finished orders of the same skill before it."""
    case_id = doc["container"].split("/")[-1]
    n = 1
    for name in store.runs():
        try:
            other = store.read_json(f"_runs/{name}")
        except (OSError, ValueError):
            continue
        if other.get("id") != doc.get("id") and other.get("skill") == doc.get("skill") and other.get("status") == "done" \
                and other.get("container", "").split("/")[-1] == case_id:
            n += 1
    return n


def play(store: FsStore, config: DomainConfig, run_name: str, replies_dir: Path, wait: bool = True) -> bool:
    """Move one order along: queued → running now; running → done once its delay has passed. No sleeping, so a
    room full of sandboxes is served in parallel by one thread. `wait=False` finishes it in one call (tests)."""
    rel = f"_runs/{run_name}"
    doc = store.read_json(rel)
    reply, replies_dir = load_reply(replies_dir, doc.get("skill", ""), config, store.root, doc["container"].split("/")[-1], _round(store, doc))
    if doc.get("status") == "queued":
        doc["status"], doc["started"], doc["taken_by"] = "running", _now(), "replay"
        store.write_json(rel, doc)
        if wait:
            return True
    elif doc.get("status") == "running":
        started = dt.datetime.fromisoformat(doc.get("started") or doc["created"])
        age = (dt.datetime.now().astimezone() - started).total_seconds()
        limit = float((reply or {}).get("delay_s", 3)) if doc.get("taken_by") == "replay" else 120.0
        if wait and age < limit:
            return False
    else:
        return False
    case_id = doc["container"].split("/")[-1]
    try:
        stage = store.find(case_id)
    except StoreError:
        stage = None
    if stage is None or reply is None:
        doc.update(status="failed", finished=_now(), exit=1, result="no prepared reply" if reply is None else "case vanished")
        store.write_json(rel, doc)
        return True
    agent = config.agent
    files_written = []
    person = next((part.split("=", 1)[1] for part in str(doc.get("note") or "").split() if part.startswith("person=")), "")
    for name, src in (reply.get("files") or {}).items():
        name = name.replace("{person}", person or "du")
        content = (replies_dir / src).read_bytes() if not str(src).startswith("inline:") else str(src)[7:].encode("utf-8")
        from ..domain import assets
        try:
            files_written.append(assets.put(store, config, case_id, name, content, name))
        except StoreError:
            try:
                store.put_bytes(case_id, name, content)
                files_written.append(name)
            except StoreError:
                pass
    e = reply.get("entry") or {}
    note = str(doc.get("note") or "").strip()
    text = str(e.get("text", "")).replace("{note}", note)
    entry = {"author": e.get("author") or (agent.name if agent else "Claude"), "status": e.get("status", "info"), "title": str(e.get("title", doc.get("skill", "")))[:120], "text": text, "files": files_written}
    if e.get("for"):
        entry["for"] = e["for"]
    with store.lock(case_id):
        if not (doc.get("background") or reply.get("silent")):        # a helper beside the people leaves its file, not a thread entry
            _append_entry(store, config, case_id, stage, entry)
        to = reply.get("to")
        if to and to in store.stages() and to != stage:
            try:
                store.move(case_id, to)
                _append_entry(store, config, case_id, to, {"author": agent.name if agent else "Claude", "status": "info", "title": config.word("stages", to, None, to),
                                                           "text": config.word("texts", "replay_moved", None, "Moved on."), "from": stage, "to": to})
            except StoreError:
                pass
    doc.update(status="done", finished=_now(), exit=0, result=entry["title"], cost_usd=float(reply.get("cost_usd", 0.0)), model=reply.get("model", "replay"),
               turns=int(reply.get("turns", 1)), duration_s=float(reply.get("delay_s", 3)))
    store.write_json(rel, doc)
    return True


class ReplayRunner:
    """A thread that watches one or many pipeline roots and plays every queued order."""

    def __init__(self, roots: "list[tuple[FsStore, DomainConfig]] | callable", replies_dir: Path, interval: float = 1.0):
        self._roots = roots
        self.replies_dir = replies_dir
        self.interval = interval
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="replay", daemon=True)

    def start(self) -> "ReplayRunner":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def once(self) -> int:
        roots = self._roots() if callable(self._roots) else self._roots
        n = 0
        for store, config in roots:
            for name in store.runs():
                try:
                    if play(store, config, name, self.replies_dir):
                        n += 1
                except Exception:          # a broken order never stops the runner
                    continue
        return n

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.once()
            except Exception:
                pass
            self._stop.wait(self.interval)
