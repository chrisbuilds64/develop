"""Stock check: read a real pipeline and say what the core would make of it. Reads only, writes nothing.

    python -m casefile.cli.inventory <pipeline-root> [--config config/pressroom] [--lang de]

For every case: stage known, meta present, label known, primary present, thread parses, persons resolve,
whose move. At the end: the counts, and everything the core could not place.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from ..config import DomainConfig
from ..domain import cases, entries as thread, turn as whose
from ..store import FsStore, StoreError


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="casefile inventory", description=__doc__)
    p.add_argument("root")
    p.add_argument("--config", default=str(Path(__file__).resolve().parents[2] / "config" / "pressroom"))
    p.add_argument("--lang", default=None)
    a = p.parse_args(argv)
    root = Path(a.root).expanduser()
    store = FsStore(root)
    config = DomainConfig.load(Path(a.config), root)
    lang = a.lang or config.lang

    unknown_stage = [s for s in store.stages() if config.stage(s) is None]
    rows, problems = [], []
    counts = Counter()
    for stage in store.stages():
        for cid in store.cases(stage):
            counts["cases"] += 1
            counts[f"stage:{stage}"] += 1
            try:
                case = cases.load(store, config, cid)
            except StoreError as exc:
                problems.append(f"{stage}/{cid}: {exc}")
                continue
            notes = []
            if "meta.json" not in case.files:
                notes.append("no meta.json")
            elif not case.meta.get("label"):
                notes.append("meta without label")
            if case.meta.get("label") and case.meta["label"] not in config.artifacts.get("formats", {}):
                notes.append(f"label {case.meta['label']} not in artifacts.json")
            if config.stage(stage) is None:
                notes.append("stage not in stages.json")
            if "configVersion" not in case.meta:
                counts["no configVersion"] += 1
            primary = config.primary(case.label)
            if primary and int(stage[:2]) >= 30 and not (case.slot(primary) and case.slot(primary).present):
                notes.append(f"primary {primary} missing")
            if "review.md" in case.files:
                raw = store.case_text(cid, "review.md")
                if raw.strip() and not case.entries:
                    notes.append("review.md has no REV entries (free-form)")
                for e in case.entries:
                    for who in (e.author, e.for_):
                        if who and config.person(who) is None:
                            notes.append(f"{e.id}: '{who}' not in people.json")
                            break
            turns = whose.turn(case, config, lang)
            main_turn = f"{turns[0].actor} → {turns[0].action}" + (f" (blocked: {', '.join(turns[0].blocked_by)})" if turns[0].blocked_by else "") if turns else "nobody"
            rows.append((stage, cid, main_turn, "; ".join(notes)))
            if notes:
                counts["with notes"] += 1

    print(f"# Stock check — {root}\n")
    print(f"{counts['cases']} cases in {len(store.stages())} stages · {counts['with notes']} with notes · {counts['no configVersion']} without configVersion\n")
    if unknown_stage:
        print("Stages not in stages.json: " + ", ".join(unknown_stage) + "\n")
    print("| stage | case | whose move | notes |\n|---|---|---|---|")
    for stage, cid, mt, notes in rows:
        print(f"| {stage} | {cid} | {mt} | {notes} |")
    if problems:
        print("\nCould not read:\n" + "\n".join(f"- {x}" for x in problems))
    by_stage = {k[6:]: v for k, v in counts.items() if k.startswith("stage:")}
    print("\nBy stage: " + ", ".join(f"{k} {v}" for k, v in sorted(by_stage.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
