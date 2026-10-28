# ADR-023: One Hand-off for Every Application, and Each Application Orders Only Its Own Skills

**Status:** Accepted (Chris, 2026-10-28)
**Date:** 2026-10-28

---

## Context

casefile is the base. Content, claims, assessments, an inbox: the same machine, specified only by the artifacts a case
holds and the skills and agents that work on it (Chris, 28.10.). Two places did not hold to that:

- **Two hand-offs.** The inbox's rule matrix opened a case in another application (`domain/handoff.py`, ADR-022); a
  claim ordering an assessment and the report returning ran through a second mechanism in the API layer, with the claims
  vocabulary written into the code (`schaden_nr`, a fixed label, a fixed year) and failures written only to a log file.
- **Skills without borders.** A skill missing from `run-policy.json` fell back to its `default` and could be ordered; the
  claims configuration even listed the content helper `interpret`. The runner linked every skill and agent of the shared
  control checkout into every run.

## Decision

1. **One hand-off in the core** (`casefile/domain/handoff.py`), two kinds, described by a spec, never by code:
   - `create`: a new case opens in the target (an order for an assessment, a mail that becomes a claim, a quote or a
     signal in PressRoom).
   - `deliver`: files reach the case that waits for them, matched by a meta key; that case takes its step (the report
     returns to its claim), or a plain note lands in its thread (a follow-up question by mail).

   The spec names target, stage, label, numbering, id slug, external reference, the source's link key, meta templates,
   files (newest version, renamed or kept, `{n}` counts), the target's entry and an optional first run. Templates read
   `{source.*}`, `{fields.*}`, `{summary}`, `{number}`, `{year}`, `{seq}`, `{ref}`, with an optional format.
2. **Two ways to choose a spec, one way to carry it out.** An action's `handover` in `stages.json` (after the step), or a
   row of the rule matrix (`regeln.json`, after a person confirms). The row's `action` stays the matrix's word
   (`create_case`, `note_to_case`, `file_away`); the target's step is `step`.
3. **Where a target points, the stage decides** (`targets.json`, ADR-022). The engine never guesses another
   application's folder. In the public demo the visitor's sandbox of the partner world is the target; only the resolving
   differs, the mechanism is the same.
4. **A failed hand-off is said where the person looks.** Before the move (rule matrix) it refuses the step, nothing moves.
   After the step (action) it stands as an open entry in the case's thread; the step itself stands.
5. **Each application orders only its own skills.** `run-policy.json` → `skills` is the list: a skill not named there is
   refused, in the core and again in the runner. The built-in question (`ask`) stays everywhere. `agents` names the
   agents a run may use. The runner links only the named skills and agents into the run's home; a tree that declares no
   `agents` keeps all of them, as before.
6. **The mail sorter's place.** The inbox and its matrix are the first consumer; the standalone mail sorter
   (`apps/mailsort`) is meant to become the core's way in for mail later, feeding the same matrix.

## Consequences

- A new connection between applications is configuration: a target in `targets.json` and a spec on an action or a row.
- A topic suggestion by mail lands in PressRoom as a signal in `05-operational-observations`, not as an idea: an idea
  enters through the ideas backlog, a person decides.
- A target only accepts files it has a slot for (`artifacts.json`); the claim gained `rueckfrage.md` for follow-ups.
- PressRoom's own `run-policy.json` at the team folder declares no `agents` yet, so its runs still see all agents until
  it does.
