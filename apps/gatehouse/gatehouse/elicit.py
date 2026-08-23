"""Follow-up questions.

The pack's stage directions and triggers are the product, not the list
of questions. This module does one thing: hand the model those rules
together with the answer just given, and ask what to probe next.

The model is given no freedom to invent an agenda. It sees the rules,
one answer, and is asked for follow-ups or nothing at all. An interview
that drifts because the model found something interesting is not
reproducible, and reproducibility is what is being sold.
"""

from __future__ import annotations

from .adapters import ModelError, Registry
from .pack import Block, Pack, Question

_PROMPT = """You are assisting an elicitation interview. You do not conduct it.

Stage directions that govern this interview:
{directions}

Follow-up triggers. If the answer below matches a cue, ask the matching
question. These are the only grounds for a follow-up:
{triggers}

Current block: {block_title}
This block is finished when:
{exit_criteria}

Question asked:
{question}

Answer given:
{answer}

Return at most two follow-up questions, one per line, no numbering, no
commentary. Return nothing at all if no trigger fires. Do not ask about
anything outside this block. Use the interviewee's own words."""


TASK = "followup"


def follow_ups(
    models: Registry, pack: Pack, block: Block, question: Question, answer: str
) -> list[str]:
    if not answer.strip():
        return []

    prompt = _PROMPT.format(
        directions="\n".join(f"- {rule}" for rule in pack.directions) or "- none given",
        triggers="\n".join(
            f"- when {t.cue} -> ask: {t.ask}" for t in pack.triggers
        )
        or "- none given",
        block_title=block.title,
        exit_criteria="\n".join(f"- {c}" for c in block.exit_criteria) or "- not defined",
        question=question.text,
        answer=answer.strip(),
    )

    try:
        reply = models.for_task(TASK).ask(TASK, prompt)
    except ModelError:
        # A failed model call must not cost the operator the answer they
        # just typed. The answer is already saved; follow-ups are not.
        return []

    return [line.strip("-• ").strip() for line in reply.splitlines() if line.strip()][:2]
