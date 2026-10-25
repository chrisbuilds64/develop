# ADR-021: Gatehouse Becomes a casefile Application; the Conversation Is a Deliverable

**Status:** Accepted (Chris, 2026-10-25)
**Date:** 2026-10-25

---

## Context

Gatehouse (ADR-010 to 012) ran as its own FastAPI app on the client's hardware: a pack of questions, a form per
block, a model call per answer and one at the end. Two things stood against it. It lived beside everything built
since: the shell, accounts with their own subscription, agents, the runner, workspaces. And the form produced
weak data: every answer carried a marker (`AS-IS / PROPOSED / OPEN`) preset to `AS-IS`, and in the first real run
53 of 55 answers kept the preset. A valid default is caught by nothing and becomes the record.

Chris, 25.10.: bring Gatehouse in the way PressRoom came in, with the assistance the other applications have;
make the elicitation engaging instead of a dull questionnaire; make the outcome something a customer recognises
as theirs. The "runs on client hardware with no extra technology" premise gives way to "our system runs inside
the client's environment, on the client's own Claude or OpenAI subscription".

## Decision

1. **An elicitation is a case.** `config/gatehouse/` is an application like PressRoom, Schadenakte and
   Gutachtenakte: preparation → conversation → clarification → canon v0.1 → second pass → closed.
2. **The conversation is a deliverable of shape `interview`**, written only by the core under the case lock
   (`domain/interview.py`). A stage that names it (`stages.json`: `"interview": "gespraech.json"`) gives every
   respondent who is not done a move of their own. Several respondents answer the same pack; nobody sees another
   person's answers while answering.
3. **No preset marker, anywhere.** An answer without the person's own classification (is / should / not sure) is
   refused. "Not sure" is a full answer.
4. **The pack stays out of this repository.** The core reads `_packs/<id>.toml` from the tree. What a question is
   for (`yields`, `seeks`) never reaches the surface; the respondent sees one `why` sentence per question.
   Triggers may carry word patterns (`match`) that the surface follows up on at once, without a model.
5. **Helpers beside people do not block them.** An order may be `background`: it is never anybody's move, leaves
   no thread entry, and writes its own collected file (`nachfragen-<person>.json`, `collects` on the deliverable).
6. **The canon is decided line by line and compiled by the core.** The evaluation helper writes the findings and a
   draft; the decider accepts, changes or rejects each line (`entscheide.json`); the action that approves
   (`requires: decided:<draft>:<decisions>`, `compile: "canon"`) writes `canon.md` with sources, a new version
   per approval. What the AI proposed holds only once a person accepted it.
7. **A case can be started from the surface** when the domain says how (`theme.create`: label, roles, meta).

## Alternatives

- **Keep the standalone app and link to it from the shell:** a second login, no agents, no runner, no
  workspaces; the outcome would stay a text nobody acts on.
- **Write answers as thread entries (steps):** one entry per answer buries the thread and makes "who said what"
  a parsing problem. The conversation is data; the thread records moves.
- **A model call per answer, synchronously:** slow, costly, and it makes the person wait. Word-pattern cues give
  the immediate follow-up; the model reads a whole chapter in the background.

## Consequences

- Engine code still names no domain: `interview`, `collects`, `background`, `answered`, `decided:`, `compile:
  canon` are mechanisms another domain can use.
- The standalone `apps/gatehouse` stays until the new path has carried one real run with somebody outside.
- Live runs need the skills `gatehouse-nachhaken` and `gatehouse-auswerten` in the shared checkout and a
  subscription or key on the orderer's account; a follow-up that cannot be billed fails quietly in its order file.
- The next step, not built here: generate the customer's own application configuration (stages, gates, roles,
  rules for their assistants) from an approved canon.
