# ADR-022: The Inbox — a Mail Is a Case, a Rule Matrix Proposes, a Person Confirms, the Core Hands Off

**Status:** Accepted (Chris, 2026-10-26)
**Date:** 2026-10-26

---

## Context

Chris, 26.10.: an application that watches one or more mailboxes, reads incoming mail with AI and, by a configurable
rule matrix, triggers actions — a claim report opens a claim file, a topic suggestion opens an idea in PressRoom. The
example is a motor claim report arriving by mail, for the second presentation on 29.10.

## Decision

1. **A mail is a case** of the application `posteingang`. One way in (`casefile.connectors.mailbox.ingest`): the
   message kept as it came (`mail.eml`), shown as a document (`mail.md`), attachments beside it; the Message-ID makes it
   idempotent. The same way serves the mailbox (IMAP over TLS, polled by the runner for live workspaces that carry
   `mailbox.json`; credentials are the named account's secrets `IMAP_USER`/`IMAP_PASSWORD`, never a file in the tree,
   never passed into a run) and a mail dropped in by hand (`POST /api/mail`, `.eml`).
2. **The rule matrix is configuration** (`regeln.json`, the tree's copy wins): per kind of mail, an action, a target,
   what travels along and how the new case is filled. It is shown in the rulebook as a table.
3. **The helper proposes, a person confirms.** `posteingang-einordnen` writes `einordnung.json` — kind, one row of the
   matrix, urgency, fields with their words, reasons quoting the mail. It never acts.
4. **The hand-off is the core's.** The confirming action carries `compile: "handoff"`; before the case moves, the core
   opens the case in the target application (`targets.json` names the target trees, written by whoever sets the
   workspace up) and records `aktion.json`. If it fails, nothing moves. Unconnected actions are shown as such.

## Consequences

- Engine code still names no domain: `connectors.mailbox`, `domain.handoff`, `compile: handoff` serve any application.
- Rows marked `approval: auto` are recorded but executed only after a person confirms, until an automatic path is decided.
- `note_to_case` (a reply to an existing claim) and the PressRoom target are next.
