"""
context_loader.py — Shared Context Assembler
ChrisBuilds64 // 2026-05-28

Loads control/shared-context/ files and assembles agent context strings.
v1: flat concatenation with priority ordering.
v2 (future): topic-relevance filtering.

Usage:
    from context_loader import load_atlas_context, load_agent_context
    context = load_atlas_context()                        # Atlas, no signature yet
    context = load_agent_context("atlas")                 # Atlas with signature injected
    context = load_agent_context("axel")                  # Axel with signature injected
"""

from pathlib import Path

SHARED_CONTEXT_PATH = Path.home() / "ChrisBuilds64/control/shared-context"
AGENTS_PATH = SHARED_CONTEXT_PATH / "agents"

# Priority order: most operationally relevant first.
# Operational state (WHAT is happening now) + decisions now live in the maintained
# source: control/context/PROJECT-STATE.md + session-logs/ — see shared-context/START-HERE.md.
# TODO: inject PROJECT-STATE.md here so Atlas gets current operational reality.
FILE_ORDER = [
    "current-intent.md",          # WHY we're doing this — prevents strategic drift
    "canonical-summary.md",       # brand/canon essentials
    "reference-frames-index.md",  # pattern library
]

# Character budget (GPT-4o-mini context window is large, but we keep it tight)
DEFAULT_CHAR_BUDGET = 8000


def _load_shared_files(budget: int) -> tuple[list[str], int]:
    """Internal: load shared context files in priority order within budget."""
    if not SHARED_CONTEXT_PATH.exists():
        return [], 0

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

    return sections, total_chars


def load_agent_context(agent: str, budget: int = DEFAULT_CHAR_BUDGET) -> str:
    """
    Load shared context + agent signature for a named instance.
    Signature is injected first (identity before operational state).

    agent: "atlas" | "axel" | "chris"
    """
    signature_path = AGENTS_PATH / f"{agent}-signature.md"
    signature_section = ""

    if signature_path.exists():
        sig_content = signature_path.read_text().strip()
        signature_section = f"=== {agent}-signature.md ===\n{sig_content}\n\n"
        sig_budget = budget - len(signature_section)
    else:
        sig_budget = budget

    shared_sections, _ = _load_shared_files(sig_budget)

    if not shared_sections and not signature_section:
        return "[shared-context empty]"

    role_headers = {
        "atlas": (
            "You are Atlas — strategist and architect in the ChrisBuilds64 system.\n"
            "Axel is the executor (Claude). Chris is the human authority.\n"
            "Your operational signature defines how you think and what you prioritize.\n"
        ),
        "axel": (
            "You are Axel — executor and implementer in the ChrisBuilds64 system.\n"
            "Atlas is the strategist (GPT). Chris is the human authority.\n"
            "Your operational signature defines how you think and what you prioritize.\n"
        ),
        "chris": (
            "This is Chris's operational profile. Human authority and decision gate.\n"
        ),
    }

    header = (
        "== ChrisBuilds64 Shared Operational Context ==\n"
        + role_headers.get(agent, f"Agent: {agent}\n")
        + "\n"
    )

    return header + signature_section + "\n\n".join(shared_sections)


def load_atlas_context(budget: int = DEFAULT_CHAR_BUDGET) -> str:
    """Legacy loader — Atlas without signature. Use load_agent_context('atlas') once signature exists."""
    sections, _ = _load_shared_files(budget)
    if not sections:
        return "[shared-context empty]"

    header = (
        "== ChrisBuilds64 Shared Operational Context ==\n"
        "You are Atlas — strategist and architect. Axel is the executor (Claude).\n"
        "Chris is the human authority. You serve Chris's intent, not your own optimization.\n\n"
    )
    return header + "\n\n".join(sections)


def load_minimal_context() -> str:
    """Minimal context: intent + state only."""
    return load_atlas_context(budget=2000)


if __name__ == "__main__":
    # Quick test: print assembled context
    ctx = load_atlas_context()
    print(f"Context assembled: {len(ctx)} characters\n")
    print(ctx[:500] + "\n...\n[first 500 chars shown]")
