# ADR-036: A Static Site as a Deploy Target

**Status:** Proposed (2026-11-14). Requirements: REQ-008.
**Date:** 2026-11-14

---

## Context

A website was published by hand: a person dragged files into an FTP client, remembered which files must not go up,
which files exist only on the server and must not be deleted, and which modes to set. The rules lived in a guide. A
mounted FTP volume showed a months-old listing without saying so. The person was the transport, and nothing proved
afterwards that what is served is what was reviewed.

ADR-032 decision 14 says a deploy target is a data point on a connector, one per stage. So far there is one kind,
our own server. A site at a shared hoster is the first production target outside our own machines.

## Decision

1. **Publishing a static site is three steps: plan, apply, verify.** The plan reads both sides and changes nothing.
   Apply uploads. Verify fetches what is served and compares it with the source.
2. **The plan is what a person approves.** It has an id over what would be written and onto what. Apply takes that id
   and refuses when the plan it computes is another one. A gate in an application later approves the same id.
3. **The module never deletes on the server and never writes a protected path.** What only the server has is listed.
   Removing a page is a decision for a person and, for now, a manual act.
4. **What is replaced is kept**, under the plan's id. Going back is uploading those files.
5. **A target is an interface with four operations** (list, read, write whole, set mode). Two kinds exist: a
   directory and FTP over explicit TLS. A further kind (SFTP, an object store) is one class.
6. **The description of a site lives with the site, credentials with neither.** This repository carries the module
   and fictional examples only.
7. **The module stands on its own**: standard library only, no import from the core. It lives in `connectors/`
   because that is where cases reach the outside; today it is run from a terminal.

## Consequences

- A site can be published in one command by someone who has no time, and the result is checked, not assumed.
- The Casefile application around it is not built here. Its shape is foreseeable: the site is a data point, a change
  to it is a case, the plan report is the evidence at the gate, the runner applies, the verify report closes the case.
- An FTP account that reaches several sites must not be handed to a run. Automation beyond a person's own terminal
  needs an account that sees one site.
- Verifying over HTTP cannot compare files the server executes. They are named as not compared.

## Alternatives considered

- **rsync or lftp mirror in a script.** Shorter, but a mirror deletes by default, has no notion of protected paths,
  and nothing a person approves stands between reading and writing.
- **A mounted volume and a file copy.** What was tried; the mount's listing was stale and there is no verification.
- **Building the Casefile application first.** The transport is the hard part and is needed now; the application is
  configuration on top of it.
