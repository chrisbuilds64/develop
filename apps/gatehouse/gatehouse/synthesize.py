"""Reading the answers back.

One model call over a finished run. Where `elicit` runs many small calls
during the interview, this is the single call that deserves the strongest
model configured, which is why it is its own task.

The instruction comes from the pack. This module only assembles what the
model is allowed to see: the questions, the answers, their markers, and
nothing else. It never sees the client's name, and there is nothing else
to see, because Gatehouse holds nothing else.
"""

from __future__ import annotations

from .adapters import ModelError, Registry
from .instance import Run
from .pack import Pack

TASK = "synthesis"

_PROMPT = """{instruction}

Stage directions that governed this interview. They constrain what may
be read into an answer, not only how it was asked:
{directions}

The answers, in the order they were given. `[OPEN]` marks something the
interviewee left unresolved, `[PROPOSED]` something suggested rather
than in place, `[AS-IS]` something they state as current practice.

{transcript}"""


class SynthesisUnavailable(Exception):
    """Raised with a message meant for an operator, not a stack trace."""


def read_back(models: Registry, pack: Pack, run: Run) -> str:
    if pack.synthesis is None:
        raise SynthesisUnavailable(
            f"Pack '{pack.name}' defines no [synthesis]. It offers no reading."
        )

    transcript = _transcript(pack, run)
    if not transcript:
        raise SynthesisUnavailable(
            "Nothing has been answered yet. There is nothing to read back."
        )

    prompt = _PROMPT.format(
        instruction=pack.synthesis.prompt.strip(),
        directions="\n".join(f"- {rule}" for rule in pack.directions) or "- none given",
        transcript="\n\n".join(transcript),
    )

    try:
        text = models.for_task(TASK).ask(TASK, prompt).strip()
    except ModelError as exc:
        # The answers are already on disk. A failed reading costs the
        # reading, never the interview.
        raise SynthesisUnavailable(str(exc)) from exc

    # An empty reply is not an empty finding list. It is a call that
    # produced nothing, and it reaches here looking exactly like a
    # reading with no findings. Under the echo adapter it is the normal
    # case and the honest answer is the same one: there is no reading.
    if not text:
        raise SynthesisUnavailable(
            "Das Modell hat nichts zurückgegeben. Ohne angebundenes Modell "
            "gibt es keine Auswertung; ist eines angebunden, war der Aufruf "
            "leer und muss wiederholt werden."
        )

    return text


def _transcript(pack: Pack, run: Run) -> list[str]:
    """Only answered questions.

    An unanswered question is deliberately absent rather than present as
    empty. Handing the model a list of blanks invites it to treat silence
    as a finding, and silence here means the form was closed early.
    """
    out = []
    for block in pack.blocks:
        for question in block.questions:
            answer = run.answers.get(question.id)
            if not answer or not answer.text.strip():
                continue
            out.append(
                f"{question.id} ({block.title}) — {question.text}\n"
                f"[{answer.marker}] {answer.text.strip()}"
            )
    return out
