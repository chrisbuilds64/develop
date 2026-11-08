# ADR-026: The Rulebook Edited in the App, as Versions

**Status:** Parts 1 to 4 accepted (Chris, 2026-11-08); part 5 deferred until after the DOAG conference (17–19.11.).
Proposed in the design hand-back, request 9.
**Date:** 2026-11-05

---

## Context

Today stages, rules and text modules live in configuration and in `_bausteine/`, read-only in the surface. The people
who run an insurer's claims desk expect to adjust a rule or a letter sentence without a developer, and an audit expects
every change to be traceable: who wrote it, who brought it into force, what stood before. A case already under way
must not change its footing in the middle.

Rules (`R-nn`) and text modules (`B-nn`) already share one store with front matter (id, kind, title, version, status,
approved_by, date), and compose already refuses a module that is not `freigegeben`. That is most of a versioned
rulebook; what is missing is the history and the way a change comes into force.

## Decision

1. **The file in force stays where it is.** `_bausteine/<id>-<slug>.md` is what compose, the AI and every reader take,
   as before. Every version also lands in `_bausteine/_fassungen/<id>.v<n>.md`; the version in force joins that history
   the first time the module is changed.
2. **A change is a draft first.** An operator writes it (`POST /api/rulebook/{id}/draft`): a new version with status
   `entwurf`, or the open draft written over. A new id starts a new module. It comes into force when a second person,
   an operator or an approver who did not write it, approves it (`…/approve`). Retiring is a version of its own with
   status `zurückgezogen` and a reason (`…/retire`). Nothing is deleted.
3. **A case keeps the rulebook it started with.** When compose writes a case's document, it takes per module the newest
   approved or retired version dated on or before the case's `created`; a module that came into force later is absent.
   A module never changed in the app is taken as it stands, since nothing earlier is recorded.
4. **Areas.** A module may name the case labels it applies to (`areas: KH, KK`). Outside them compose passes over it.
   `/api/rules` shows areas, an open draft and the number of versions; `GET /api/rulebook/{id}` the whole history and
   whether the viewer may edit or approve.
5. **Workflow steps (proposed, not built).** Editing `stages.json` from the app needs the same promise: cases under way
   keep the workflow they started with. Cases already carry `configVersion`. The proposal: the tree keeps
   `_ablauf/stages.v<n>.json` with the same draft and four-eyes rules, `DomainConfig` loads the version a case names,
   and `turn()`/`step()` take the case's config instead of the one config. A version may only add or rename stages
   and actions; removing a stage that holds cases is refused. This touches every read path, so it waits for Chris.

## Review amendments (2026-11-08)

- **To the second.** A version records `in_force_since` (date and time) when it is approved or retired. A case with a
  start time takes the versions in force at that moment; a case whose start is a bare date takes the whole day, as
  before. Without this, a version approved at 14:00 reached a case created at 09:00 the same day.
- **Four eyes by person.** A draft records `drafted_by_id`; approval compares ids, not display names. Older drafts
  without the id fall back to the name.
- **Every entry point checks the id** (`R-08`, `B-19`) before it reaches a file name or pattern.

## Alternatives

- **Edit the files in git.** Keeps one history, but puts a developer between the claims desk and its rules.
- **Version the whole rulebook as one unit.** Simpler to pin, but every sentence change would bump every module, and
  the composed document could no longer quote "B-05, Fassung 3".

## Consequences

- Rule and letter changes are self-service and leave an audit trail per module.
- A document composed for a case names the module versions it used (as before); those are now the versions in force
  when the case started.
- Workflow editing stays read-only until part 5 is decided.
