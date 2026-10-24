# ADR-017: Three Stages on One Server, Test Data Is Production Cloned

**Status:** Accepted (Chris, 2026-10-24)
**Date:** 2026-10-24

---

## Context

The PressRoom ran as one instance: one team folder, one cockpit, one runner, all production. Every
change to the cockpit, the runner or a skill was tried on the real pipeline or on a laptop against a
synced copy. Development houses fail at the same point: test environments exist but have no
representative data, because the data depends on systems nobody configured for testing.

## Decision

- **Three stages, ENTW, TEST and PROD, on the same server**, told apart by the URL path: `/` is
  production, `/test/` and `/entw/` are stages. Without a prefix it is always production.
- **Each stage owns its data: a Nextcloud team folder, a WebDAV mount, a cockpit, a runner.** The
  storage path of a stage is the same as production's (team folder, read from the disk, written
  through the mount), so a stage tests the real path, not a shortcut.
- **Test data is production, cloned.** A stage is created from a copy of the production folder and
  re-cloned on demand. The copy leaves the run queue behind and carries a marker
  (`flow/environment.json`). Nothing flows back; production is never a clone target.
- **Code is staged, rules are not.** `develop` is checked out per stage at its own reference and the
  cockpit installed from it. Canon and skills are shared and pulled before every run: they are the
  same rules for everyone and must be current everywhere.
- **The stages are configuration** (`envs.toml`), and one tool (`infra/pressroom/pressroom-env`)
  makes the server match it: team folder, mount, units, workspace, nginx locations.
- **A run from the button knows what a session at the keyboard knows.** The runner builds the
  operating context from a curated manifest (`control/shared-context/context-manifest.json`) and
  hands it to the headless session as an appended system prompt. A SessionStart hook cannot carry
  it: Claude Code keeps hook output above a few kilobytes out of the context (observed 2026-10-24).

## Consequences

- A developer always has a pipeline that looks like production, including its history, images and
  review threads, and can break it without consequence.
- Three cockpits, three runners and three davfs2 mounts on a 4 GB machine: measured 2.3 GB available
  after creation, before any run. A headless run adds 200 to 400 MB while it lasts.
- Promotion is a `deploy <stage> --ref` with a human in between TEST and PROD, by hand today; a tag
  and a pipeline can follow without changing the model.
- Nextcloud is, for the machine, only a storage adapter now. When every writer runs on the server,
  plain directories owned by the service suffice, with Nextcloud mounting them as external storage
  for people. That is the next step, not this one.
