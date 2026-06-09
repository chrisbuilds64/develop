"""
03_requirements_dev_review.py — Requirements → Dev → Review Pipeline
ChrisBuilds64 LangGraph Experiment // 2026-06-09

The problem this solves:
  A structured SDLC flow where AI proposes requirements, develops code,
  and reviews it — with Chris as the human gate at every critical step.

Graph architecture:
  START → [define_requirements] → [human_approve_requirements]
                                          |
                                     (approved)
                                          ↓
                                     [develop] → [review] → [human_approve_result]
                                         ↑                          |
                                         └──────── revise ──────────┘

Run: .venv/bin/python 03_requirements_dev_review.py "build a user login API"
"""

from typing import TypedDict, Optional
from pathlib import Path

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
import anthropic

# --- Client ---

ANTHROPIC_KEY = (Path.home() / ".secrets/chrisbuilds64/chrisbuilds64.antrophic.api").read_text().strip()
claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)


# --- State ---
# Everything the graph needs to pass between nodes.

class SDLCState(TypedDict):
    topic: str               # what we're building
    requirements: str        # AI-proposed requirements
    code: str                # AI-generated code
    review_result: str       # AI review of the code
    revision_note: str       # Chris's latest instruction
    iteration: int           # how many dev→review cycles we've done


# --- Nodes ---

def define_requirements(state: SDLCState) -> dict:
    """AI proposes requirements for what Chris wants to build."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": f"""
You are a senior software architect. Propose clear, concise requirements for:

{state['topic']}

Format:
- 5-8 bullet points
- Functional requirements only (what the system must do)
- No implementation details yet
- Each point: one sentence, specific and testable
"""}]
    )

    return {"requirements": response.content[0].text}


def human_approve_requirements(state: SDLCState) -> Command:
    """Chris reads the requirements and approves or gives feedback."""

    display = f"""
{'=' * 60}
REQUIREMENTS REVIEW
{'=' * 60}

Topic: {state['topic']}

Proposed Requirements:
{state['requirements']}

{'=' * 60}
Type "approve" to proceed to development.
Or describe what to change.
{'=' * 60}"""

    human_input = interrupt(display)

    if human_input.strip().lower() == "approve":
        return Command(goto="develop")

    return Command(
        goto="refine_requirements",
        update={"revision_note": human_input.strip()}
    )


def refine_requirements(state: SDLCState) -> dict:
    """AI incorporates Chris's feedback into the existing requirements."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": f"""
Update these requirements based on the feedback. Keep what is good, incorporate the change.

Current requirements:
{state['requirements']}

Feedback:
{state['revision_note']}

Return the updated requirements list. Same format as before.
"""}]
    )

    return {"requirements": response.content[0].text, "revision_note": ""}


def develop(state: SDLCState) -> dict:
    """AI writes code based on the approved requirements."""

    revision_section = ""
    if state.get("revision_note"):
        revision_section = f"""
Previous review feedback from Chris:
{state['revision_note']}

Address this feedback in the new version.
"""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": f"""
You are a senior software engineer. Implement the following requirements.

Requirements:
{state['requirements']}
{revision_section}
Write clean, production-ready code. Include brief inline comments only where the WHY is non-obvious.
"""}]
    )

    return {
        "code": response.content[0].text,
        "iteration": state.get("iteration", 0) + 1,
        "revision_note": ""
    }


def review(state: SDLCState) -> dict:
    """AI reviews the generated code against the requirements."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[{"role": "user", "content": f"""
You are a senior code reviewer. Review the following code against the requirements.

Requirements:
{state['requirements']}

Code:
{state['code']}

Review format:
- Requirements coverage: which are met, which are missing
- Critical issues (bugs, security, correctness)
- Minor issues (style, clarity)
- Verdict: PASS or REVISE (with specific reason)
Be direct. No padding.
"""}]
    )

    return {"review_result": response.content[0].text}


def human_approve_result(state: SDLCState) -> Command:
    """Chris reads the code + review and makes the final call."""

    display = f"""
{'=' * 60}
ITERATION {state['iteration']} — DEVELOPMENT REVIEW
{'=' * 60}

REQUIREMENTS:
{state['requirements']}

CODE:
{state['code']}

AI REVIEW:
{state['review_result']}

{'=' * 60}
Type "approve" to finish. Or describe what to change.
{'=' * 60}"""

    human_input = interrupt(display)

    if human_input.strip().lower() == "approve":
        return Command(goto=END)

    return Command(
        goto="develop",
        update={"revision_note": human_input.strip()}
    )


# --- Graph ---

def build_graph():
    builder = StateGraph(SDLCState)

    builder.add_node("define_requirements", define_requirements)
    builder.add_node("human_approve_requirements", human_approve_requirements)
    builder.add_node("refine_requirements", refine_requirements)
    builder.add_node("develop", develop)
    builder.add_node("review", review)
    builder.add_node("human_approve_result", human_approve_result)

    builder.add_edge(START, "define_requirements")
    builder.add_edge("define_requirements", "human_approve_requirements")
    builder.add_edge("refine_requirements", "human_approve_requirements")
    # human_approve_requirements routes via Command(goto=...)
    builder.add_edge("develop", "review")
    builder.add_edge("review", "human_approve_result")
    # human_approve_result routes via Command(goto=...)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# --- CLI Runner ---

if __name__ == "__main__":
    import sys

    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "build a simple REST endpoint for user login"

    graph = build_graph()
    config = {"configurable": {"thread_id": "sdlc-001"}}

    initial_state: SDLCState = {
        "topic": topic,
        "requirements": "",
        "code": "",
        "review_result": "",
        "revision_note": "",
        "iteration": 0,
    }

    print(f"\nStarting SDLC flow: {topic}\n")
    result = graph.invoke(initial_state, config)

    while "__interrupt__" in result:
        print(result["__interrupt__"][0].value)
        human_input = input("\nYour decision: ").strip()
        result = graph.invoke(Command(resume=human_input), config)

    print("\n" + "=" * 60)
    print("DONE")
    print(f"Iterations: {result.get('iteration', '?')}")
    print("=" * 60)
