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


def load_reply(replies_dir: Path, skill: str) -> dict | None:
    p = replies_dir / f"{skill}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


def play(store: FsStore, config: DomainConfig, run_name: str, replies_dir: Path, wait: bool = True) -> bool:
    """Play one order to its end. Returns True when it was played."""
    rel = f"_runs/{run_name}"
    doc = store.read_json(rel)
    if doc.get("status") != "queued":
        return False
    reply = load_reply(replies_dir, doc.get("skill", ""))
    doc["status"], doc["started"], doc["taken_by"] = "running", _now(), "replay"
    store.write_json(rel, doc)
    if wait:
        time.sleep(float((reply or {}).get("delay_s", 3)))
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
    for name, src in (reply.get("files") or {}).items():
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
    entry = {"author": agent.name if agent else "Claude", "status": e.get("status", "info"), "title": str(e.get("title", doc.get("skill", "")))[:120], "text": text, "files": files_written}
    if e.get("for"):
        entry["for"] = e["for"]
    with store.lock(case_id):
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
