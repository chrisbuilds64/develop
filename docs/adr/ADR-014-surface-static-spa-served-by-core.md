# ADR-014: The Surface Is a Static Single-Page App Served by the Core

**Status:** Accepted (Chris, 2026-10-21)
**Date:** 2026-10-21

---

## Context

The new surface is phone-first, shows one decision per screen, animates a case moving to its next station, accepts files dropped onto empty frames, and must run the same way on a private server and inside a customer's network.

## Decision

- React + Vite + TypeScript, TanStack Router and Query, built to static files and served by the core (FastAPI). Installable as a PWA.
- Types come from the core: Pydantic models → OpenAPI → generated TypeScript types; CI fails on drift.
- One `tokens.css` holds every colour, size and radius; a lint rule forbids colour values elsewhere. The single accent is named `--your-move` and means only "this waits for you".
- Updates by polling (20–30 s) at first; server-sent events and web push when a deployment needs them.

## Alternatives

- **Next.js on a hosted platform:** server rendering brings nothing to a signed-in app with few visits, adds a second server runtime, and complicates on-premise review. Hosted platforms remain fine for a marketing site.
- **Server-rendered templates (the current surface):** cannot carry the interactions the redesign depends on without growing ad-hoc script.

## Consequences

- No Node.js in production; the static folder ships with the core.
- The old surface stays reachable, frozen, until the new one is accepted, then it is removed.

## Amended 2026-11-10: the built surface is not in git

The built surface (`apps/casefile/web/dist/`) was checked in while the stages had no Node. Its file names carry a
content hash, so every merged change to the surface renamed them, and every other open pull request that touched the
surface conflicted on files nobody wrote — three times in one evening on a helper's pull request, each time a hand merge
and another CI run.

From now on the build is never in git. CI builds the surface (`guards`) to prove it compiles, and every deploy builds it
on the server from the source it ships (`pressroom-env deploy`: `npm ci`, `npm run build`, refused when `dist/index.html`
is missing). The servers have Node 22. A conflict in a pull request is again one in source, and worth a look.
