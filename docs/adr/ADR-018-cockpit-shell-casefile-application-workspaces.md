# ADR-018: The Cockpit Is the Shell, casefile the Application, the Workspace the Unit

**Status:** Accepted (Chris, 2026-10-24)
**Date:** 2026-10-24

---

## Context

Two surfaces existed over the same kind of folder tree: the cockpit (server-rendered, the production
PressRoom, tools behind buttons) and casefile (the rebuilt core and React surface made for the claims
demo, ADR-013 to 016). Chris, 24.10.: the casefile stand is the truth; carry it into the current stand so
that there is one main line to develop from. And: data directories must be switchable — a person creates
a sandbox as a **workspace**, any number of PressRooms and claims files run side by side, personal or
shared, all of it configuration.

## Decision

1. **The cockpit is the shell.** It owns who you are (login, roles), what you configure (accounts:
   settings, secrets), what you may open, the audit, the dashboard and the side menu. It renders no
   case itself any more; the workshop modules stay as tools behind the menu.
2. **casefile is the application.** A domain configuration (`config/<domain>/`) plus the core is an
   application: PressRoom, Schadenakte, Gutachtenakte. The shell mounts one casefile app per workspace
   under `/w/<id>/`, in its own process and URL, with the cockpit's login as the app's identity
   (`Settings.identity`); casefile's own cookie is not read there.
3. **The workspace is the unit.** A workspace is one tree under one application, with an owner or
   shared, with members. The registry (`workspaces.json`, beside `users.json`, one per stage) lists
   applications and workspaces. A person creates a workspace from the application's template or as a
   clone of a workspace they may see; orders and journals start empty; nothing flows back.
4. **The runner serves the registry.** One runner per stage polls every live workspace's queue and
   gives each run a HOME of its own in which `~/ChrisBuilds64/pressroom` points at that workspace, so
   the skills — the same files the person uses at the keyboard — stay untouched.
5. **One look.** casefile's `tokens.css` is the palette of the shell too: blue only for "this waits for
   you", Instrument Sans, IBM Plex Mono. The surface is one build served under any prefix (the core
   writes the base into `index.html` per mount).
6. **Writes through the mount where the sync server must see them.** `FsStore(root, write_root)`:
   read from the disk, write through the WebDAV mount — until the data moves to the disk and Nextcloud
   becomes a window onto it (SYS-66).

## Consequences

- One main line: new behaviour is built in casefile; the cockpit's pipeline module is the classic
  view and goes when nobody opens it any more.
- A person's identity is one login for every workspace; whether they are a *person* in a given tree
  is that tree's `people.json`. The surface says so instead of offering a picker.
- Sample worlds (claims, e-report) are workspaces in `replay` mode: prepared answers, no Claude, and
  they keep the person picker because their people are invented.
- `web/dist` is checked in for now: the stages have no Node. A CI build replaces that.
- A workspace entry will grow from `root`/`write_root` into a list of components — storage (a local
  directory, a team folder, another server), an index (Oracle on one machine or another), later events —
  each spoken through an adapter, each configured per stage. The application declares what it needs.
- Rights inside a workspace are casefile's roles; rights to a workspace are membership. Per-account
  agents and signatures (SYS-70) extend the account, not this decision.
