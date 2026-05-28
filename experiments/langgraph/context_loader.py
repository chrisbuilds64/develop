"""
context_loader.py — Shared Context Assembler for Atlas
ChrisBuilds64 // 2026-05-28

Loads control/shared-context/ files and assembles an Atlas context string.
v1: flat concatenation with priority ordering.
v2 (future): topic-relevance filtering.

Usage:
    from context_loader import load_atlas_context
    context = load_atlas_context()          # all files
    context = load_atlas_context(focus="content")  # filtered (v2)
"""

from pathlib import Path

SHARED_CONTEXT_PATH = Path.home() / "ChrisBuilds64/control/shared-context"

# Priority order: most operationally relevant first
FILE_ORDER = [
    "current-intent.md",       # WHY we're doing this — prevents strategic drift
    "current-state.md",        # WHAT is happening right now
    "active-projects.md",      # active context anchors
    "recent-decisions.md",     # what changed recently
    "open-loops.md",           # unresolved questions — prevents fake certainty
    "canonical-summary.md",    # brand/canon essentials (longest, load last)
    "reference-frames-index.md",  # pattern library
]

# Character budget for Atlas (GPT-4o-mini context window is large, but we keep it tight)
DEFAULT_CHAR_BUDGET = 8000


def load_atlas_context(budget: int = DEFAULT_CHAR_BUDGET) -> str:
    """
    Load and assemble shared context for Atlas injection.
    Respects character budget — truncates lower-priority files if needed.
    """
    if not SHARED_CONTEXT_PATH.exists():
        return "[shared-context not found — operating without context]"

    sections = []
    total_chars = 0

    for filename in FILE_ORDER:
        filepath = SHARED_CONTEXT_PATH / filename
        if not filepath.exists():
            continue

        content = filepath.read_text().strip()
        section = f"=== {filename} ===\n{content}"
        section_chars = len(section)

        if total_chars + section_chars > budget:
            remaining = budget - total_chars
            if remaining > 200:
                section = section[:remaining] + "\n[...truncated for context budget]"
                sections.append(section)
            break

        sections.append(section)
        total_chars += section_chars

    if not sections:
        return "[shared-context empty]"

    header = (
        "== ChrisBuilds64 Shared Operational Context ==\n"
        "This is the current state of the system you are operating in.\n"
        "You are Atlas — strategist and architect. Axel is the executor (Claude).\n"
        "Chris is the human authority. You serve Chris's intent, not your own optimization.\n\n"
    )

    return header + "\n\n".join(sections)


def load_minimal_context() -> str:
    """
    Minimal context: intent + state only. For quick single-turn queries.
    """
    return load_atlas_context(budget=2000)


if __name__ == "__main__":
    # Quick test: print assembled context
    ctx = load_atlas_context()
    print(f"Context assembled: {len(ctx)} characters\n")
    print(ctx[:500] + "\n...\n[first 500 chars shown]")
