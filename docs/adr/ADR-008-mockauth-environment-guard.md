# ADR-008: MockAuth for Development, Fail-Closed Guard for Production

**Status:** Accepted
**Date:** 2026-07-19 (reconstructed)
**Provenance:** Reconstruction. The auth architecture was built in early 2026 (REQ-001) without a recorded decision. Reconstructed from code evidence (`adapters/auth/`, `api/dependencies.py`) during the 2026-07-19 repo consolidation — one day after the guard proved itself in production.

---

## Context

The backend needs authenticated endpoints, but a real auth provider (Clerk was the intended choice) was not yet integrated. Development and testing must not depend on an external auth service. The risk to manage: a development-only auth mechanism silently reaching production.

## Decision

Auth is an exchangeable port (`AuthProvider` interface) with environment-gated wiring in `api/dependencies.py`:

- `ENV` in (`test`, `development`, `local`) → `MockAuthAdapter` (well-known test users, token format `test-<user>`).
- `ENV` in (`production`, `staging`) → intended for `ClerkAdapter` (not yet implemented).
- **Any other case → `RuntimeError`. Fail-closed:** no ENV value silently falls back to mock auth. Until ClerkAdapter exists, production auth endpoints fail rather than accept mock tokens.

## Alternatives

- **Mock auth everywhere until Clerk lands:** fastest, but a production API accepting `test-chris` as a valid token is an open door.
- **Block development on real auth integration:** safe, but couples all feature work to an external service decision.
- **Feature flag instead of ENV gating:** flags can be flipped ad hoc; ENV is set per environment by deployment (ADR-004) and not casually changed.

## Why this design

- Development stays fully local and offline-capable; tests get deterministic users.
- The port interface means Clerk integration is an adapter drop-in, not a refactor.
- Fail-closed beats fail-open for auth: the guard converts "forgot to configure auth" into a loud 500 instead of a silent bypass.

## Consequences

**Benefits:**
- The guard is enforced by code, not documentation. Proven in production 2026-07-19: a rebuild replaced a months-old pre-guard image, the guard activated, and all auth endpoints on `ENV=production` now return 500 — the production database is no longer reachable through the API. Deliberately left in this state until Clerk v2 (decision Chris, 2026-07-19).
- Unknown or misconfigured ENV values cannot degrade into mock auth.

**Trade-offs:**
- Production has no working auth until ClerkAdapter is implemented — acceptable while no production feature requires login.
- Mock tokens are deliberately permissive in dev (any non-empty token maps to a default user); dev environments must never be exposed publicly.
