"""
02_skill_review_graph.py — Parallel Proposal Review
ChrisBuilds64 LangGraph Experiment // 2026-05-31

What this solves:
  Given any proposal (skill design, architecture decision, content plan,
  workshop question), two agents review it independently and simultaneously.
  Chris sees both reviews side by side and makes a decision.

Graph architecture (ADR-001):
  START → [axel] (parallel)
        → [aris] (parallel)
  Both  → [chris_gate] → END

Independence guarantee: Aris sees NO Axel output before writing his review.
Both agents work only from the original proposal.

Axel  = Claude Sonnet-4-6  (executor: bottom-up, concrete requirements)
Aris  = GPT-4o             (local tactical reviewer: top-down, strategic perspective)
Chris = interrupt gate     (reads both reviews, enters decision)

Note: Aris is NOT Atlas. Aris is stateless (no history, API-only).
      Atlas is the strategic advisor who communicates via CMD documents.

Run: .venv/bin/python 02_skill_review_graph.py "your proposal here"
"""

from typing import TypedDict
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
import anthropic
import openai

# --- Clients ---

ANTHROPIC_KEY = (Path.home() / ".secrets/chrisbuilds64/chrisbuilds64.antrophic.api").read_text().strip()
OPENAI_KEY    = (Path.home() / ".secrets/chrisbuilds64/openai.api").read_text().strip()

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
gpt    = openai.OpenAI(api_key=OPENAI_KEY)


# --- State (per ADR-001) ---

class ReviewState(TypedDict):
    proposal:       str   # input: the thing being reviewed
    axel_review:    str   # Axel's independent assessment
    aris_review:   str   # Atlas's independent assessment
    human_decision: str   # Chris's decision or redirect
    final_output:   str   # assembled review document


# --- Nodes ---

def axel_node(state: ReviewState) -> dict:
    """Claude: executor perspective. Bottom-up. What are the requirements? What breaks?"""

    prompt = f"""You are Axel — executor and implementer in the ChrisBuilds64 production system.
You think bottom-up: concrete requirements first, critical path before architecture.

Review this proposal:

{state['proposal']}

Your review (150-200 words):
- What are the concrete requirements this must satisfy?
- What works? What is missing or will break?
- What is the critical path — the single most important thing that must be true?
- What is the simplest implementation that does not create future debt?

State your conclusion first. Be specific. No abstractions without operational grounding."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    return {"axel_review": response.content[0].text}


def aris_node(state: ReviewState) -> dict:
    """GPT-4o: Aris — local tactical reviewer. Top-down. Strategic perspective, structural coherence."""

    prompt = f"""You are Aris — local tactical reviewer in the ChrisBuilds64 production system.
You think top-down: structural coherence, strategic fit, hidden assumptions.

Review this proposal:

{state['proposal']}

Your review (150-200 words):
- Where does this fit in the larger system or strategy?
- What structural decisions does this imply or foreclose?
- What is the strategic risk or opportunity here?
- Is the framing correct, or does this proposal solve the wrong problem?

State your conclusion first. Challenge assumptions where necessary. Be direct.
Take a position — do not offer "both options could work."."""

    response = gpt.chat.completions.create(
        model="gpt-4o",
        max_completion_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    return {"aris_review": response.choices[0].message.content}


def chris_gate(state: ReviewState) -> Command:
    """Human-in-the-loop gate. Chris reads both independent reviews and decides."""

    sep  = "=" * 60
    dash = "-" * 40

    display = f"""
{sep}
PROPOSAL REVIEW
{sep}

PROPOSAL:
{state['proposal']}

{sep}
AXEL  —  Claude Sonnet  —  Executor Perspective
{dash}
{state['axel_review']}

{sep}
ARIS   —  GPT-4o  —  Strategic Perspective (local, stateless)
{dash}
{state['aris_review']}

{sep}
Both agents reviewed independently.
Neither saw the other's output before writing.

Enter "approved" to accept, or type your decision / redirect:
{sep}"""

    human_input = interrupt(display)
    decision = human_input.strip()

    final_output = "\n".join([
        "PROPOSAL REVIEW  —  ChrisBuilds64",
        sep,
        "",
        "PROPOSAL:",
        state['proposal'],
        "",
        "AXEL (Executor Perspective):",
        state['axel_review'],
        "",
        "ARIS (Strategic Perspective — local, stateless):",
        state['aris_review'],
        "",
        "DECISION:",
        decision,
        sep,
    ])

    return Command(
        goto=END,
        update={
            "human_decision": decision,
            "final_output":   final_output,
        }
    )


# --- Graph ---

def build_graph():
    builder = StateGraph(ReviewState)

    builder.add_node("axel",       axel_node)
    builder.add_node("aris",       aris_node)
    builder.add_node("chris_gate", chris_gate)

    # Parallel fan-out from START — both agents run simultaneously
    builder.add_edge(START,  "axel")
    builder.add_edge(START,  "aris")

    # LangGraph waits for both before chris_gate runs (barrier semantics)
    builder.add_edge("axel",  "chris_gate")
    builder.add_edge("aris", "chris_gate")

    return builder.compile(checkpointer=MemorySaver())


# --- CLI Runner ---

if __name__ == "__main__":
    import sys

    proposal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Should this team treat LangSmith as a debugging tool or as an audit layer?"
    )

    graph  = build_graph()
    config = {"configurable": {"thread_id": "review-001"}}

    initial_state: ReviewState = {
        "proposal":       proposal,
        "axel_review":    "",
        "aris_review":   "",
        "human_decision": "",
        "final_output":   "",
    }

    print(f"\nReviewing: {proposal}")
    print("Running parallel review (Axel + Atlas)...\n")

    result = graph.invoke(initial_state, config)

    while "__interrupt__" in result:
        print(result["__interrupt__"][0].value)
        human_input = input("\nYour decision: ").strip()
        result = graph.invoke(Command(resume=human_input), config)

    print("\n" + sep if (sep := "=" * 60) else "")
    print("REVIEW COMPLETE")
    print(sep)
    if result.get("final_output"):
        print(result["final_output"])
