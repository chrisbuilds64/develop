"""Run state and the files it produces.

Two artifacts per run, both in the instance directory:

  run.json      the state, machine-owned, diffable
  interview.md  the same content rendered for a human, rewritten on
                every answer

The rendered file is what goes into the client's version control and
what someone reads two years later. The JSON exists because parsing
prose back into state is fragile, and a governance tool that loses
answers to a parser bug has no business being installed anywhere.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .pack import Pack


@dataclass
class Answer:
    question_id: str
    question: str
    text: str
    follow_ups: list[str] = field(default_factory=list)
    marker: str = "AS-IS"  # AS-IS | PROPOSED | OPEN
    answered_at: str = ""


@dataclass
class Run:
    pack_name: str
    pack_version: str
    client: str
    started_at: str
    current_block: str
    answers: dict[str, Answer] = field(default_factory=dict)
    closed_blocks: list[str] = field(default_factory=list)


class Instance:
    def __init__(self, path: Path, pack: Pack) -> None:
        self._path = path
        self._pack = pack
        self._path.mkdir(parents=True, exist_ok=True)

    @property
    def state_file(self) -> Path:
        return self._path / "run.json"

    @property
    def interview_file(self) -> Path:
        return self._path / "interview.md"

    def start(self, client: str) -> Run:
        run = Run(
            pack_name=self._pack.name,
            pack_version=self._pack.version,
            client=client,
            started_at=datetime.now(timezone.utc).isoformat(),
            current_block=self._pack.blocks[0].id,
        )
        self.save(run)
        return run

    def load(self) -> Run | None:
        if not self.state_file.exists():
            return None
        raw = json.loads(self.state_file.read_text(encoding="utf-8"))
        raw["answers"] = {k: Answer(**v) for k, v in raw.get("answers", {}).items()}
        return Run(**raw)

    def save(self, run: Run) -> None:
        payload = asdict(run)
        self.state_file.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.interview_file.write_text(self._render(run), encoding="utf-8")

    def record(self, run: Run, question_id: str, text: str, marker: str = "AS-IS") -> Answer:
        question = self._question(question_id)
        answer = run.answers.get(question_id)
        if answer is None:
            answer = Answer(question_id=question_id, question=question.text, text=text)
            run.answers[question_id] = answer
        answer.text = text
        answer.marker = marker
        answer.answered_at = datetime.now(timezone.utc).isoformat()
        self.save(run)
        return answer

    def _question(self, question_id: str):
        for block in self._pack.blocks:
            for question in block.questions:
                if question.id == question_id:
                    return question
        raise KeyError(f"No question '{question_id}' in pack '{self._pack.name}'.")

    def _render(self, run: Run) -> str:
        lines = [
            f"# Elicitation — {run.client}",
            "",
            f"**Pack:** {run.pack_name} {run.pack_version}",
            f"**Started:** {run.started_at}",
            "",
            "Markers: `[AS-IS]` what is, `[PROPOSED]` what someone suggests, "
            "`[OPEN]` unresolved. An unmarked draft is a claim, not a record.",
            "",
        ]
        for block in self._pack.blocks:
            closed = " (closed)" if block.id in run.closed_blocks else ""
            lines += ["---", "", f"## {block.title}{closed}", ""]
            for question in block.questions:
                answer = run.answers.get(question.id)
                lines.append(f"**{question.id} {question.text}**")
                lines.append("")
                if answer and answer.text.strip():
                    lines.append(f"`[{answer.marker}]` {answer.text.strip()}")
                    for follow_up in answer.follow_ups:
                        lines += ["", f"> follow-up: {follow_up}"]
                else:
                    lines.append("_unanswered_")
                lines.append("")
            if block.exit_criteria:
                lines.append("*Exit criteria:*")
                lines += [f"- {c}" for c in block.exit_criteria]
                lines.append("")
        return "\n".join(lines)
