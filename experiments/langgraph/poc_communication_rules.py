"""
poc_communication_rules.py — POC: Communication Rules Canonicalization
ChrisBuilds64 // 2026-05-28

Single-topic run of the Axel+Atlas review graph.
Topic: Should LinkedIn communication/reply rules be consolidated into the canonical hierarchy?

Run: .venv/bin/python poc_communication_rules.py
Then type "approve" or a revision instruction when prompted.
"""

from typing import TypedDict, Optional
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
import anthropic
import openai
from context_loader import load_atlas_context

ANTHROPIC_KEY = (Path.home() / ".secrets/chrisbuilds64/chrisbuilds64.antrophic.api").read_text().strip()
OPENAI_KEY = (Path.home() / ".secrets/chrisbuilds64/openai.api").read_text().strip()

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
gpt = openai.OpenAI(api_key=OPENAI_KEY)


TOPIC = """Should LinkedIn engagement and reply rules be consolidated into the canonical hierarchy,
and if so — how? Currently these rules are scattered across multiple locations with no single authority."""

CONTEXT = load_atlas_context()  # loaded from control/shared-context/


class ReviewState(TypedDict):
    topic: str
    context: str
    axel_analysis: str
    atlas_analysis: str
    revision_note: str
    iteration: int
    approved: bool


def axel_node(state: ReviewState) -> dict:
    revision_section = ""
    if state.get("revision_note"):
        revision_section = f"""
--- Chris's revision request ---
{state['revision_note']}
Address this specifically. Don't repeat previous analysis verbatim."""

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
    separator = "=" * 60
    display = f"""
{separator}
ITERATION {state['iteration']} — CHRIS GATE
{separator}

AXEL (Claude — Executor Perspective)
{'-' * 40}
{state['axel_analysis']}

ATLAS (GPT — Strategist Perspective)
{'-' * 40}
{state['atlas_analysis']}

{separator}
Type "approve" to accept, or give a revision instruction.
{separator}"""

    human_input = interrupt(display)

    if human_input.strip().lower() == "approve":
        return Command(goto=END, update={"approved": True, "revision_note": ""})

    return Command(
        goto="axel",
        update={"revision_note": human_input.strip(), "approved": False}
    )


def build_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("axel", axel_node)
    builder.add_node("atlas", atlas_node)
    builder.add_node("chris_gate", chris_gate)
    builder.add_edge(START, "axel")
    builder.add_edge("axel", "atlas")
    builder.add_edge("atlas", "chris_gate")
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    graph = build_graph()
    config = {"configurable": {"thread_id": "comms-rules-poc-001"}}

    initial_state: ReviewState = {
        "topic": TOPIC,
        "context": CONTEXT,
        "axel_analysis": "",
        "atlas_analysis": "",
        "revision_note": "",
        "iteration": 0,
        "approved": False,
    }

    print(f"\nPOC: Communication Rules Canonicalization\n")
    result = graph.invoke(initial_state, config)

    while "__interrupt__" in result:
        print(result["__interrupt__"][0].value)
        human_input = input("\nYour decision: ").strip()
        result = graph.invoke(Command(resume=human_input), config)

    print("\n" + "=" * 60)
    print("APPROVED — Session complete.")
    print(f"Iterations: {result.get('iteration', '?')}")
    print("=" * 60)
