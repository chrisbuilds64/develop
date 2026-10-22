"""The contracts. Pydantic models are the source; OpenAPI and the TypeScript types derive from them (ADR-014).

Nothing in here names a domain. "Podcast" and "Schaden" live in the configuration (ADR-015).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------------- configuration

class Action(BaseModel):
    """One thing a person can do with a case while it stands in a stage."""
    id: str
    label: str                                   # vocabulary key or the word itself
    to: str | None = None                        # target stage folder; None = the case stays
    run: str | None = None                       # a skill to order instead of (or besides) moving
    requires: list[str] = Field(default_factory=list)   # deliverable file names that must be present
    four_eyes: bool = False                      # the person acting must not be the author of the primary deliverable
    entry_status: str = "info"                   # the status the thread entry carries ("approved", "info", …)
    payload: list[str] = Field(default_factory=list)    # payload fields the surface must send, e.g. ["amount", "date"]
    actor: str | None = None                     # who may do it; None = the stage's turn
    handover: dict | None = None                 # demo: after the step, files go to a partner world (world, match, files, action, by, note)


class AutoRun(BaseModel):
    """When a file lands in this stage, a helper is ordered: 'the invoice arrives, the AI reconciles'."""
    on_file: str
    skill: str
    note: str = ""


class Stage(BaseModel):
    folder: str                                  # "30-review-human"
    key: str                                     # "review" — the word key and the station on the line
    turn: str | None = None                      # "role:approver", "person:akhil", "claude", or None (nobody's move)
    actions: list[Action] = Field(default_factory=list)
    group: str = "other"                         # where the surface lists it: you | claude | others | date | planned | out | ideas | archive
    auto: list[AutoRun] = Field(default_factory=list)


class Deliverable(BaseModel):
    file: str                                    # "substack.md", "thumbnail-16x9.png"
    stage: str = ""                              # where it is due
    by: str = ""                                 # who makes it: a skill, a role, "human"
    shape: str = "text"                          # text | image-16x9 | image-4x5 | video-9x16 | pdf | money
    required: bool = False


class Person(BaseModel):
    id: str
    name: str
    kind: Literal["human", "agent"] = "human"
    roles: list[str] = Field(default_factory=list)
    deputy: str | None = None                    # who stands in when this person is away


# ----------------------------------------------------------------------------- the case as read

class Entry(BaseModel):
    """One item of the thread (review.md): `## REV-NNN — title`, a head line, text."""
    id: str
    title: str
    date: str = ""
    author: str = ""
    for_: str | None = Field(default=None, alias="for")
    status: str = "info"
    stage: str = ""
    resolves: str | None = None
    step: str | None = None                      # the step that wrote it (ADR-013)
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    amount: str | None = None
    files: list[str] = Field(default_factory=list)   # deliverables this entry delivered
    text: str = ""

    model_config = {"populate_by_name": True}


class FileVersion(BaseModel):
    name: str                                    # the file as it sits in the folder
    version: int = 0                             # 0 = unversioned (the first), then .v2, .v3 …
    size: int = 0


class Slot(BaseModel):
    """A deliverable's place in the case: filled with versions, or empty with its shape."""
    file: str
    shape: str
    required: bool
    due_stage: str
    by: str
    versions: list[FileVersion] = Field(default_factory=list)

    @property
    def present(self) -> bool:
        return bool(self.versions)

    @property
    def newest(self) -> FileVersion | None:
        return self.versions[-1] if self.versions else None


class Run(BaseModel):
    id: str
    skill: str
    container: str
    requested_by: str
    runner: str = "claude-code"
    status: Literal["queued", "running", "done", "failed"] = "queued"
    created: str
    started: str | None = None
    finished: str | None = None
    note: str | None = None
    log: str | None = None
    result: str | None = None
    cost_usd: float | None = None
    model: str | None = None
    turns: int | None = None
    duration_s: float | None = None


class Case(BaseModel):
    """A case as the core reads it: everything `turn()` needs, nothing more."""
    id: str                                      # the folder name
    stage: str                                   # the stage folder it stands in
    meta: dict = Field(default_factory=dict)
    files: list[str] = Field(default_factory=list)
    slots: list[Slot] = Field(default_factory=list)
    entries: list[Entry] = Field(default_factory=list)
    runs: list[Run] = Field(default_factory=list)
    since: str = ""                              # ISO time the case entered its stage, as far as the thread knows

    @property
    def label(self) -> str:
        return str(self.meta.get("label") or self.id.split("-", 1)[0])

    @property
    def last_run(self) -> Run | None:
        return self.runs[-1] if self.runs else None

    def slot(self, file: str) -> Slot | None:
        return next((s for s in self.slots if s.file == file), None)


# ----------------------------------------------------------------------------- whose move

class Turn(BaseModel):
    """One move that waits. Element 0 of `turn()` is the main one."""
    actor: str                                   # person id, "role:<role>", or "claude"
    action: str                                  # action id from the configuration, or a built-in: "answer", "see_failure", "wait"
    label: str                                   # the word the surface shows
    reason: str                                  # one sentence
    blocked_by: list[str]
    since: str = ""
    entry: str | None = None                     # the entry this move answers, when it is an answer
    payload: list[str] = Field(default_factory=list)   # what the surface must ask for: amount, date, url, note


# ----------------------------------------------------------------------------- a step

class StepRequest(BaseModel):
    action: str
    step_id: str                                 # the surface's idempotency key
    payload: dict = Field(default_factory=dict)  # amount, date, note, text, resolves …


class StepResult(BaseModel):
    ok: bool
    step_id: str
    case: str
    action: str
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    entry: str | None = None                     # the thread entry written
    run: str | None = None                       # the run ordered
    reason: str = ""                             # why it was refused, in a sentence
    replayed: bool = False                       # the same step id came in before; this is its recorded outcome

    model_config = {"populate_by_name": True}


class Journal(BaseModel):
    """`_steps/<step_id>.json` — the record a step leaves before it touches the case (ADR-013)."""
    step_id: str
    case: str
    action: str
    by: str
    status: Literal["intent", "done", "refused"] = "intent"
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    entry: str | None = None
    run: str | None = None
    payload: dict = Field(default_factory=dict)
    created: str
    finished: str | None = None
    reason: str = ""

    model_config = {"populate_by_name": True}
