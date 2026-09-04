"""Canon pack loading.

A pack holds everything that makes a run reproducible: the stage
directions, the blocks in order, the follow-up triggers, and the exit
criteria. None of it lives in this code. Gatehouse without a pack asks
nothing, which is the point of the separation.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class PackError(Exception):
    """Raised with a message meant for an operator, not a stack trace."""


@dataclass(frozen=True)
class Question:
    id: str
    text: str
    yields: str = ""


@dataclass(frozen=True)
class Block:
    id: str
    title: str
    questions: list[Question]
    exit_criteria: list[str] = field(default_factory=list)
    note: str = ""


@dataclass(frozen=True)
class Trigger:
    cue: str
    ask: str
    seeks: str = ""


@dataclass(frozen=True)
class Synthesis:
    """What a pack allows a run to say about its own answers.

    The instruction lives in the pack and not in this module for the
    same reason the questions do: the code is public and the canon is
    the product. What a reading may claim is a canon decision.
    """

    title: str
    lead: str
    prompt: str


@dataclass(frozen=True)
class Pack:
    name: str
    version: str
    language: str
    directions: list[str]
    blocks: list[Block]
    triggers: list[Trigger]
    layers: list[str] = field(default_factory=list)
    synthesis: Synthesis | None = None

    def block(self, block_id: str) -> Block:
        for candidate in self.blocks:
            if candidate.id == block_id:
                return candidate
        raise PackError(f"No block '{block_id}' in pack '{self.name}'.")


def load(directory: Path, _seen: set[Path] | None = None) -> Pack:
    """Load a pack, resolving `extends` into a domain layer if present."""
    manifest = directory / "pack.toml"
    if not manifest.exists():
        raise PackError(f"No pack.toml in {directory}.")

    _seen = _seen or set()
    resolved = directory.resolve()
    if resolved in _seen:
        raise PackError(f"Pack '{directory.name}' extends itself, directly or in a cycle.")
    _seen.add(resolved)

    with manifest.open("rb") as fh:
        raw = tomllib.load(fh)

    meta = raw.get("pack", {})
    for key in ("name", "version"):
        if not meta.get(key):
            raise PackError(f"[pack] {key} is required in {manifest}.")

    blocks = [_block(entry, manifest) for entry in raw.get("block", [])]
    triggers = [
        Trigger(cue=t["cue"], ask=t["ask"], seeks=t.get("seeks", ""))
        for t in raw.get("trigger", [])
    ]
    directions = list(raw.get("directions", {}).get("rules", []))
    synthesis = _synthesis(raw.get("synthesis"), manifest)

    base_name = meta.get("extends")
    if base_name:
        base = load(directory.parent / base_name, _seen)
        blocks = _extend(base, blocks, raw.get("block_extension", []), manifest)
        triggers = base.triggers + triggers
        directions = base.directions + directions
        # The one place a layer may replace rather than append. A domain
        # layer that must not change how its own answers are read would
        # be unable to say anything domain-specific about them.
        synthesis = synthesis or base.synthesis
        layers = base.layers + [f"{meta['name']} {meta['version']}"]
    else:
        if raw.get("block_extension"):
            raise PackError(
                f"{manifest} defines block_extension but no [pack] extends. "
                "Extensions only make sense on top of a core pack."
            )
        layers = [f"{meta['name']} {meta['version']}"]

    if not blocks:
        raise PackError(f"Pack {meta['name']} defines no blocks.")

    duplicates = {b.id for b in blocks if [x.id for x in blocks].count(b.id) > 1}
    if duplicates:
        raise PackError(f"Duplicate block id(s) {sorted(duplicates)} in {manifest}.")

    return Pack(
        name=meta["name"],
        version=meta["version"],
        language=meta.get("language", "en"),
        directions=directions,
        blocks=blocks,
        triggers=triggers,
        layers=layers,
        synthesis=synthesis,
    )


def _extend(
    base: Pack, new_blocks: list[Block], extensions: list[dict], manifest: Path
) -> list[Block]:
    """Apply a layer to a core pack.

    A layer adds and never overrides. It may append questions and exit
    criteria to a core block, and it may append entirely new blocks. It
    may not remove a block, reorder them, replace a core question, or
    change a core block's title.

    This is enforced here rather than documented, because a layer that
    can change core behaviour means the core is no longer identical
    across clients, and the whole licensing model rests on it being so.
    """
    base_ids = {b.id for b in base.blocks}

    for block in new_blocks:
        if block.id in base_ids:
            raise PackError(
                f"Block '{block.id}' already exists in the core pack. A layer "
                f"cannot replace a core block. Use [[block_extension]] with "
                f"id = \"{block.id}\" to add questions to it."
            )

    additions: dict[str, dict] = {}
    for entry in extensions:
        block_id = entry.get("id")
        if not block_id:
            raise PackError(f"Every block_extension needs an id in {manifest}.")
        if block_id not in base_ids:
            raise PackError(
                f"block_extension targets '{block_id}', which is not a core "
                f"block. Core blocks: {', '.join(sorted(base_ids))}."
            )
        for forbidden in ("title", "note"):
            if forbidden in entry:
                raise PackError(
                    f"block_extension '{block_id}' sets '{forbidden}'. A layer "
                    "adds questions and exit criteria; it does not restate the core."
                )
        additions.setdefault(block_id, {"question": [], "exit_criteria": []})
        additions[block_id]["question"] += entry.get("question", [])
        additions[block_id]["exit_criteria"] += entry.get("exit_criteria", [])

    merged: list[Block] = []
    for block in base.blocks:
        extra = additions.get(block.id)
        if not extra:
            merged.append(block)
            continue
        questions = list(block.questions)
        for index, q in enumerate(extra["question"]):
            questions.append(
                Question(
                    id=q.get("id") or f"{block.id}.+{index + 1}",
                    text=q["text"],
                    yields=q.get("yields", ""),
                )
            )
        merged.append(
            Block(
                id=block.id,
                title=block.title,
                questions=questions,
                exit_criteria=block.exit_criteria + extra["exit_criteria"],
                note=block.note,
            )
        )

    return merged + new_blocks


def _block(entry: dict, manifest: Path) -> Block:
    for key in ("id", "title"):
        if not entry.get(key):
            raise PackError(f"Every block needs an {key} in {manifest}.")

    questions = [
        Question(
            id=q.get("id") or f"{entry['id']}.{index + 1}",
            text=q["text"],
            yields=q.get("yields", ""),
        )
        for index, q in enumerate(entry.get("question", []))
    ]
    if not questions:
        raise PackError(f"Block '{entry['id']}' defines no questions.")

    return Block(
        id=entry["id"],
        title=entry["title"],
        questions=questions,
        exit_criteria=list(entry.get("exit_criteria", [])),
        note=entry.get("note", ""),
    )


def _synthesis(raw: dict | None, manifest: Path) -> Synthesis | None:
    """A pack without [synthesis] simply offers no reading.

    Absence is a valid state, not an error: a pack meant for a guided
    two-hour session may deliberately leave the reading to the person
    who sat through it.
    """
    if raw is None:
        return None

    prompt = (raw.get("prompt") or "").strip()
    if not prompt:
        raise PackError(
            f"[synthesis] in {manifest} defines no prompt. A reading with no "
            "instruction would be the model's own agenda, not the pack's."
        )

    return Synthesis(
        title=(raw.get("title") or "What your answers say").strip(),
        lead=(raw.get("lead") or "").strip(),
        prompt=prompt,
    )
