# ADR-029: Gate Protocols

**Status:** Proposed (2026-11-09), amended 2026-11-10 (acceptance criteria, the canon as Definition of Done, the
developer's acceptance on ENTW, every application). Waits for *Accepted*. Requirements: REQ-003.
**Date:** 2026-11-09

---

## Context

A gate in casefile opens when a file is there (`requires`) and the person who holds it decides. What the person checked
before deciding is not recorded. For an acceptance that is the gap that hurts most: after a deploy somebody has to look
at the installed system, and somebody else at what it does for the business, and both have to say what they looked at.

Shipyard shows it on its own work. The ENTW, TEST and PROD records (`release.md`, `test.md`, `prod.md`) are written by
the agent that deployed; the acceptance rests on the agent's report. For a database change it shows worse: objects are
compiled into the database, not shipped compiled. A deploy can succeed, the schema can match the repository, and a
package can still be invalid — the first user to call it gets the error. "We delivered, and nobody looked whether
everything compiles" is where changes break.

The practice for this is old and the same everywhere: installation, operational and performance qualification (IQ, OQ,
PQ) in regulated industries, test scripts and an acceptance record in customer projects, post-deployment verification in
operations, gate criteria in Stage-Gate, the checklist in aviation and surgery. Fixed criteria before the work, worked
through by a person, each with a result, evidence, a name and a time; the gate opens when every must-item passed.

casefile already has the shape: the interview (ADR-021) collects answers per person from a pack, with no default, and a
person decides drafted lines one by one. A protocol is the same with a check in place of a question and a verdict in
place of an answer.

## Decision

1. **A gate protocol is a deliverable of the case** (`shape: "protocol"`), one per gate that asks for it. It is written
   only through the core, under the case lock, like every other record.
2. **Its standing items come from a template** in the application's configuration (`protocols/<id>.json`): what is
   checked at this gate for every case — the version on the stage, the services, the migrations, no new invalid objects.
   A workspace may have its own template in its tree (`_protocols/`), as packs are (house rules are somebody's).
   Whether a person may replace the template or only add items is a right of a role in the workspace, not a fixed rule.
3. **Case items are added for the case.** A helper drafts them from the task (what to try, what to expect); the person
   who holds the gate strikes or adds items before working through them. Every item says where it came from.
4. **Each item is a question with a type and a criterion** (amended 2026-11-09, product owner): yes/no (must be yes),
   a number (equal to a prediction, within a range, below a limit), a choice (one of the allowed values), or text, a
   file or a link (must be there, as evidence). An answer that misses its criterion fails the item. Not applicable needs
   a reason. **Nothing is preset** — not a tick, not an answer (the interview's 53 of 55 lesson).
5. **Who may answer is a role on the question, not a kind of participant** (amended 2026-11-09): roles and functions,
   not person or machine. A question whose criterion is objective (the tag is on `main`, no new invalid objects, rows
   changed = rows predicted) may be answered for good by an agent in its role. A question that needs judgement (can the
   business work with it, does the scope match the task) has a person's role by default; there an agent may observe and
   attach evidence, and the person answers. **The gate itself is still opened only by the role that holds it**, with a
   name and a time: the questionnaire is the condition, not the decision.
6. **Must and should.** Each item is a must-item or a should-item (Stage-Gate's must-meet and should-meet). **The gate
   reads the protocol:** an action names it (`protocol: "<id>"`) and is offered only when every must-item passed or is not
   applicable with a reason. A failed must-item offers the way back instead, with the item as its reason. A failed
   should-item does not block; it is shown at the decision and stays in the sealed record.
7. **A completed protocol is sealed** with the person and the time and compiled into a readable record beside it. A
   change sent back and deployed again gets a new protocol version; the old one stays (C-06).
8. **The same mechanism for every application.** Shipyard first: installation check on ENTW (developer), business
   acceptance on TEST (a role of its own), production check on PROD (developer). The database change file next, with
   "no new invalid objects against the baseline before the deploy" as a standing, agent-observed item.

## Amended 2026-11-10: acceptance criteria, the canon as Definition of Done, every application

The product owner (2026-11-10), from practice: a user story carries acceptance criteria; a model drafts them well from
the requirement; a team keeps a Definition of Done. The protocol takes all three in.

9. **Acceptance criteria belong to the task.** When a helper writes the task (`task.md`), it drafts the acceptance
   criteria from the requirement as a list of its own: each a statement, how it is checked (one of the item types of
   decision 4) and where (the developer's acceptance on ENTW, the business acceptance on TEST, or both). Confirming the
   task confirms its criteria — the Definition of Ready. A task without acceptance criteria is not offered for
   confirmation. The criteria become the case items of the protocols (decision 3), each naming its criterion
   (`task AC-3`), so every item can be traced to the requirement and every criterion to the item that checked it.
10. **The canon is the Definition of Done.** Standing items are not written into each template: a template includes the
    Definition of Done of its domain from the canon (`canon/<domain>/definition-of-done.md`: per kind of gate, the
    rules to check, each pointing at its canon rule). A rule that a machine can check (a guard, a linter, the tests, a
    naming check) names its check; an agent in its role runs it and answers with the output as evidence (decision 5).
    A rule that needs judgement stays a person's item. Changing the canon changes every protocol that includes it, from
    its next version on; a sealed protocol keeps the rules it was checked against.
11. **On ENTW the developer accepts, technically and functionally.** The installation check of decision 8 becomes the
    developer's acceptance: the technical items (installation, Definition of Done) and the acceptance criteria marked
    for ENTW. TEST stays the business acceptance (the criteria marked for TEST, by a role that is not the developer);
    PROD the production check.
12. **Every application has its gates this way.** PressRoom's review gate is a protocol with the editorial Definition of
    Done (language, tone, the content boundaries, the symbolic language) and a fact check answered by the role
    `fact_checker` — an agent — with its report as evidence; the reviewer decides. A case with parts (ADR-033) can ask
    "every part closed" as an item the core answers.

## Consequences

- Every acceptance rests on a person's evidence in their role, not on the report of the agent that deployed. ADR-027's
  `test.md` and `prod.md` become protocols; the verify helper fills observations, the person decides.
- The business side gets instructions for exactly this change, written before it tests, and a place to say what it saw.
- Shipyard needs a role for the business acceptance (`acceptance`), never held by the change's developer. With us the
  product owner holds it in personal union, or a peer (Akhil) as peer review; the configuration names both.
- New core code: the protocol file and its steps (a sibling of `domain/interview.py`), the gate condition, the surface
  to work through a protocol. It needs better input fields; it comes after the editor (SYS-127).
- An invalid object after a deploy becomes a failed item with its evidence, not a user's first error message.

## Alternatives considered

- **A checklist as a Markdown file with boxes.** Rejected: a box can be ticked by anyone, preset in the template, and
  the gate cannot read it.
- **Only automated checks in the pipeline.** Rejected as the whole answer: they cover what a machine can see. Whether
  the business can work with the change only a person can say. Automated checks become observations inside the protocol.
- **One protocol for the whole release.** Rejected: installation and business acceptance are different roles with
  different questions at different stages.
