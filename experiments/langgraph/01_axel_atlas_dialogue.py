"""
01_axel_atlas_dialogue.py — Axel + Atlas Multi-Agent Review
ChrisBuilds64 LangGraph Experiment // 2026-05-26

The problem this solves:
  Chris manually copies context between Axel (Claude) and Atlas (GPT).
  This graph eliminates that — both agents see the same topic,
  produce complementary perspectives, Chris reviews and routes.

Graph architecture:
  START → [axel] → [atlas] → [chris_gate] → END
                      ↑            |
                      └── revise ──┘

Axel  = Claude Sonnet   (executor perspective: bottom-up, implementation, precision)
Atlas = GPT-4o-mini     (strategist perspective: top-down, structure, frameworks)
Chris = interrupt gate  (reads both outputs, approves or redirects)

Run: .venv/bin/python 01_axel_atlas_dialogue.py "your topic here"
"""

from typing import TypedDict, Optional
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
import anthropic
import openai

# --- Clients ---

ANTHROPIC_KEY = (Path.home() / ".secrets/chrisbuilds64/chrisbuilds64.antrophic.api").read_text().strip()
OPENAI_KEY = (Path.home() / ".secrets/chrisbuilds64/openai.api").read_text().strip()

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
gpt = openai.OpenAI(api_key=OPENAI_KEY)


# --- State ---

class ReviewState(TypedDict):
    topic: str
    context: str
    axel_analysis: str
    atlas_analysis: str
    revision_note: str       # latest instruction from Chris (empty = first run)
    iteration: int
    approved: bool


# --- Nodes ---

def axel_node(state: ReviewState) -> dict:
    """Claude: executor perspective. What works in practice? What breaks?"""

    revision_section = ""
    if state.get("revision_note"):
        revision_section = f"""
--- Chris's revision request ---
{state['revision_note']}
Address this specifically. Don't repeat your previous analysis verbatim."""

    prompt = f"""You are Axel — executor and implementer in the ChrisBuilds64 production system.
You think bottom-up: what the concrete requirements are, what works in practice, what fails.

Topic: {state['topic']}

Context:
{state['context']}
{revision_section}

Analysis (150-200 words, implementation perspective):
- What are the concrete requirements?
- What works, what breaks?
- What's the critical path?
Be specific. No abstractions without grounding."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "axel_analysis": response.content[0].text,
        "iteration": state.get("iteration", 0) + 1
    }


def atlas_node(state: ReviewState) -> dict:
    """GPT: strategist perspective. Where does this fit? What are the systemic implications?"""

    revision_section = ""
    if state.get("revision_note"):
        revision_section = f"""
--- Chris's revision request ---
{state['revision_note']}
Factor this into your strategic assessment."""

    prompt = f"""You are Atlas — strategist and architect in the ChrisBuilds64 production system.
You think top-down: frameworks, structure, strategic coherence, systemic implications.

Topic: {state['topic']}

Context:
{state['context']}

Axel's implementation analysis:
{state['axel_analysis']}
{revision_section}

Strategic assessment (150-200 words):
- Where does this fit in the larger system?
- What structural decisions are implied?
- What's the strategic risk or opportunity?
Build on Axel's concrete findings — go one level up. Don't repeat what he said."""

    response = gpt.chat.completions.create(
        model="gpt-4o-mini",
        max_completion_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    return {"atlas_analysis": response.choices[0].message.content}


def chris_gate(state: ReviewState) -> Command:
    """Human-in-the-loop. Chris reads both perspectives, decides: approve or revise."""

    separator = "=" * 60
    display = f"""
{separator}
ITERATION {state['iteration']} — REVIEW
{separator}

TOPIC: {state['topic']}

AXEL (Claude — Executor Perspective)
{'-' * 40}
{state['axel_analysis']}

ATLAS (GPT — Strategist Perspective)
{'-' * 40}
{state['atlas_analysis']}

{separator}
Enter "approve" to accept, or type a revision instruction.
{separator}"""

    # Pause execution here. Chris reads the display and responds.
    human_input = interrupt(display)

    if human_input.strip().lower() == "approve":
        return Command(goto=END, update={"approved": True, "revision_note": ""})

    return Command(
        goto="axel",
        update={"revision_note": human_input.strip(), "approved": False}
    )


# --- Graph ---

def build_graph():
    builder = StateGraph(ReviewState)

    builder.add_node("axel", axel_node)
    builder.add_node("atlas", atlas_node)
    builder.add_node("chris_gate", chris_gate)

    builder.add_edge(START, "axel")
    builder.add_edge("axel", "atlas")
    builder.add_edge("atlas", "chris_gate")
    # chris_gate routes dynamically via Command(goto=...) — no static edge needed

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# --- CLI Runner ---

if __name__ == "__main__":
    import sys

    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Should /produce and /asset be merged into a single skill?"
    )

    context = """\
ChrisBuilds64 Brand Operating System — production pipeline:
  /produce skill: generates text deliverables + image prompts, moves to 30-review-human
  /asset skill:   generates images (Nano Banana Pro) + overlays, moves to 50-ready-to-publish

FN-055 (first canonical run) observation:
  Full production happened in a single session — no intermediate stage.
  The produce → human review → asset split added friction without clear value.

Canonical hierarchy: Tier 1 (control/principles) > Tier 2 (brand/world) > Tier 4 (production skills).
Skills are Tier 4. They must derive from, never contradict, Tier 1-3."""

    graph = build_graph()
    config = {"configurable": {"thread_id": "review-001"}}

    initial_state: ReviewState = {
        "topic": topic,
        "context": context,
        "axel_analysis": "",
        "atlas_analysis": "",
        "revision_note": "",
        "iteration": 0,
        "approved": False,
    }

    print(f"\nStarting review: {topic}\n")
    result = graph.invoke(initial_state, config)

    # Interrupt loop — runs until Chris approves
    while "__interrupt__" in result:
        print(result["__interrupt__"][0].value)
        human_input = input("\nYour decision: ").strip()
        result = graph.invoke(Command(resume=human_input), config)

    print("\n" + "=" * 60)
    print("APPROVED")
    print(f"Total iterations: {result.get('iteration', '?')}")
    print("=" * 60)
