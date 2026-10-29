# ADR-024: The Stack — One Gate at a Time, the Shell Falls

**Status:** Accepted (Chris, 2026-10-29)
**Date:** 2026-10-29

---

## Context

Ten screenshots of the product on 2026-10-28 showed the same inherited frame in every application: menu, case list,
case with progress line, thread column, main action at the far edge, plus a kanban and a list view and a dashboard of
equal cards. Everything visible at once, nothing in front. "32 things wait for you" was a sum without a top; "what is
decided" appeared nowhere, although gates are the product principle.

Three independent design directions (a worklist of moves, the case as a document, a stack of gates), a verified
reference collection and a skeptical review with measurements all removed the same thing: the frame. They converged on
one column, one piece in full depth, four fixed positions in every piece (*present · missing · your move · before*),
provenance on every line, and a locked gate shown as a sentence with its condition instead of a second button. Chris
chose the stack of gates (planning: `control/planning/2026-10-29_ux-durchbruch/`).

## Decision

1. **A move has a kind.** `turn.enrich()` classifies every `Turn`: `date` (the case carries a date), `seal` (the gate
   is stamped), `gate` (the move changes the stage or answers a question), `gap` (the move waits for something: a
   deliverable, an answer, a decision), `nudge` (starts a helper, delivers, waits). A move that waits is a gap whatever
   its gate would be.
2. **The stack has a rule, and it is configuration.** `turns_for()` orders by `order` in `stages.json`, default
   `date → seal → gate → gap → nudge`; inside a group by date, then the longest-waiting first. The person does not sort;
   the person filters. The rule is shown at the head of the stack.
3. **The move is a sentence.** The vocabulary carries `headlines` and `locks` per action with the placeholders
   `{title}`, `{label}`, `{missing}`, `{first}`, `{n}`, and `requires` words for tokens (`shape:image`, `answered`,
   `decided:`). The engine fills them; the surface shows them. Where no template exists, the headline is
   `{label}: {title}` and the lock `{label}; opens once {missing} is in the file`. No prose the product cannot generate.
4. **The gate is the screen.** One piece in full depth: place line, headline, the path with dates, the situation as four
   lines (place · with whom since when · missing · last), the evidence with what is missing first (dashed circle), then
   what is present as rows with version · person · date, exactly one filled button, the locked gate as a sentence with
   a lock, the second legitimate way as a text link. Behind it, folded in place: thread, all files, record, rules.
   "After" is the rest of the stack as rows with their one action. What counts is gates, not moves; ideas stand in the
   reserve.
5. **The shell falls, the overview stays in sight.** Menu, case list, tile wall, thread column and modal dialogs
   leave. The pipeline stays visible: a band over the stack with every stage and its count (a graphic, click to
   filter), and in the gate the stations as a dotted line with dates under the headline. Kanban and stacked list stay
   as views behind a visible switch ("stack · kanban · list"); the stack is the entry, never the only view. Every row
   carries the case's cover (format tint, label, number), every piece shows all its slots without unfolding. A session
   with an agent is a position in the piece, not a dialog. *(Corrected after Chris's first look on 2026-10-29: "the
   pipeline is gone", "list and kanban are gone", "only text, before it was at least a graphic overview".)*
6. **What is not in this round:** the seal bound to a file version that breaks when a new version arrives (the engine
   has `seal` as a flag on the step only); the stack across workspaces in the cockpit; glass mode; a reading view for
   a case nobody has a move on.

## Consequences

- `Turn` gains `kind`, `headline`, `lock`, `date`; `DomainConfig` gains `order`. Views carry enriched moves.
- Each domain owes sentence templates per action, in two languages; a missing template falls back to a plain one.
- The React surface is rebuilt in steps on branch `ux-entscheidung`: first `Case.tsx` becomes the gate, the shell stays
  so the demo flows keep running; then the list becomes "after" and the shell falls; then the cockpit stack.
- Production is untouched until Chris has clicked through on ENTW.
