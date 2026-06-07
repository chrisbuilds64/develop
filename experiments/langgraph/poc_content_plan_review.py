"""
poc_content_plan_review.py — Content Arc Review: June 2026
ChrisBuilds64 // 2026-05-28

Axel + Atlas review the June content arc.
Does the sequence make strategic sense?
Any gaps, timing risks, workshop misalignments?
"""

from typing import TypedDict
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

TOPIC = """Review the June 2026 content arc: 12 themes on Human-Orchestrated AI Systems.

Does the sequence make strategic sense?
Are there gaps, redundancies, or timing risks?
How well does it align with the Italy Workshop (2026-06-19) and DOAG (deadline 2026-06-08)?
Any themes that are too thin, too speculative, or out of order given the anti-patterns defined?

Current status:
- FN-055: PUBLISHED
- FN-056: PUBLISHED today (2026-05-28)
- FN-057: PRODUCTION READY (50-ready-to-publish), publish Monday 2026-06-02
- FN-058 through FN-066: PLANNED, need /interpret runs"""

CONTENT_ARC = """\
== June 2026 Content Arc: Human-Orchestrated AI Systems ==

Arc positioning: Every post is a concrete observation from actually building and operating these systems.
No theory. No futurism. Operational reality.

Anti-patterns for this arc:
- Do NOT position LangGraph or Axel/Atlas/Chris as novelty theater
- Do NOT speculate about AGI or future AI capabilities
- Do NOT present automation fantasies or "AI replaces humans" narratives
- Do NOT theorize without operational grounding

12 themes in narrative sequence:

1. FN-055 — AI Amplification and Pattern Recognition [PUBLISHED]
   AI amplifies what you bring to it. Blind spot amplifier.

2. FN-056 — AI Projects Fail Before the First Prompt [PUBLISHED today]
   Failure is in missing definitions: ownership, validation, handoff, review, "correct".

3. FN-057 — Why Ownership Becomes MORE Important With AI [PRODUCTION READY]
   AI doesn't reduce need for ownership clarity — it amplifies the cost of its absence.
   "The system produces output. Whose output is it? Who validates it?"

4. FN-058 — The Hidden Cost of Vibe Coding [PLANNED]
   Initial velocity, governance debt. Link to Italy Workshop Unit 1, Vibe Coding Tax concept.

5. FN-059 — Human-in-the-Loop Is Not a Limitation [PLANNED]
   Human review gates are architecture, not overhead. Force multipliers when placed correctly.
   Seed: Italy Workshop Unit 3, Block 2.5.

6. FN-060 — Multi-Agent Systems Are Organizational Design [PLANNED]
   Multi-agent AI surfaces organizational design problems.
   Governance questions requiring engineering to implement.

7. FN-061 — Validation Is the New Senior Engineering Skill [PLANNED]
   As AI generates faster, the scarcest skill is validation.
   Define "correct," evaluate output, distinguish plausible from correct.

8. FN-062 — The Future Is Not Autonomous Agents [PLANNED]
   Autonomous agents remove governance without replacing it.
   Orchestrated cognitive systems: human intent remains the driver.

9. FN-063 — AI Reveals Existing Organizational Fragmentation [PLANNED]
   AI as structural mirror. Organizations struggling with AI governance were already fragmented.

10. FN-064 — The Practitioner's Gate [PLANNED]
    Difference between generated output and production-ready output.
    Publishable/deployable output = governance quality at the handoff, not model quality.

11. FN-065 — Orchestration as Core Engineering Discipline [PLANNED]
    LangGraph, routing, states, ownership.
    Cognitive routing, responsibility transitions, validation states, human checkpoints.

12. FN-066 — What We Learned Building a Real Multi-Agent Workflow [PLANNED]
    Lived operational lessons from Axel/Atlas/Chris system.
    Target: before or just after Italy Workshop (2026-06-19).

== Publish Schedule ==
Rhythm: Monday + Thursday, 07:30
Gap rule: never more than 4 days. Never two posts same day.
Next: FN-057 Monday 2026-06-02, FN-058 Thursday 2026-06-05
Italy Workshop: 2026-06-19
DOAG deadline: 2026-06-08 (portal submission, PDFs to Jan Timmering still pending)
"""


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
        revision_section = f"\n--- Chris's revision request ---\n{state['revision_note']}\nAddress specifically."

    prompt = f"""You are Axel — executor in the ChrisBuilds64 system. Bottom-up, implementation, what actually works.

Topic: {state['topic']}

Shared operational context:
{state['context']}

Content arc detail:
{CONTENT_ARC}
{revision_section}

Analysis (150-200 words):
- What works in this sequence? What's solid?
- What breaks, what's risky, what's missing?
- Any specific sequencing problems given the Italy Workshop (Jun 19) and DOAG deadline (Jun 8)?
Be concrete. Reference specific theme numbers."""

    response = claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return {"axel_analysis": response.content[0].text, "iteration": state.get("iteration", 0) + 1}


def atlas_node(state: ReviewState) -> dict:
    revision_section = ""
    if state.get("revision_note"):
        revision_section = f"\n--- Chris's revision request ---\n{state['revision_note']}\nFactor into strategic assessment."

    prompt = f"""You are Atlas — strategist in the ChrisBuilds64 system. Top-down, structure, strategic coherence.

Topic: {state['topic']}

Shared operational context:
{state['context']}

Content arc detail:
{CONTENT_ARC}

Axel's analysis:
{state['axel_analysis']}
{revision_section}

Strategic assessment (150-200 words):
- Does the arc have strategic coherence as a whole?
- What is the cumulative reader journey across 12 themes?
- Where are the narrative risks (redundancy, fatigue, too abstract)?
- How does this arc position Chris in the market?
Build on Axel's findings. Go one level up. Don't repeat what he said."""

    response = gpt.chat.completions.create(
        model="gpt-4o-mini",
        max_completion_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )
    return {"atlas_analysis": response.choices[0].message.content}


def chris_gate(state: ReviewState) -> Command:
    separator = "=" * 60
    display = f"""
{separator}
ITERATION {state['iteration']} — CONTENT ARC REVIEW
{separator}

AXEL (Executor — what works / what breaks)
{'-' * 40}
{state['axel_analysis']}

ATLAS (Strategist — coherence / positioning / risks)
{'-' * 40}
{state['atlas_analysis']}

{separator}
"approve" to accept — or give a revision instruction.
{separator}"""

    human_input = interrupt(display)
    if human_input.strip().lower() == "approve":
        return Command(goto=END, update={"approved": True, "revision_note": ""})
    return Command(goto="axel", update={"revision_note": human_input.strip(), "approved": False})


def build_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("axel", axel_node)
    builder.add_node("atlas", atlas_node)
    builder.add_node("chris_gate", chris_gate)
    builder.add_edge(START, "axel")
    builder.add_edge("axel", "atlas")
    builder.add_edge("atlas", "chris_gate")
    return builder.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    graph = build_graph()
    config = {"configurable": {"thread_id": "content-plan-review-001"}}

    initial_state: ReviewState = {
        "topic": TOPIC,
        "context": load_atlas_context(),
        "axel_analysis": "",
        "atlas_analysis": "",
        "revision_note": "",
        "iteration": 0,
        "approved": False,
    }

    print("\nContent Arc Review — June 2026\n")
    result = graph.invoke(initial_state, config)

    while "__interrupt__" in result:
        print(result["__interrupt__"][0].value)
        human_input = input("\nYour decision: ").strip()
        result = graph.invoke(Command(resume=human_input), config)

    print("\n" + "=" * 60)
    print(f"APPROVED — {result.get('iteration', '?')} iteration(s)")
    print("=" * 60)
