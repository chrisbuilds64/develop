# ADR-004: Three-Environment Strategy

**Status:** Accepted
**Date:** 2026-04-22
**Provenance:** Migrated from archived `chrisbuilds64/sdlc` (there ADR-003), 2026-07-19.

---

## Context

Software that touches production data and runs public-facing services requires a clear separation between development, validation, and production. The question is how many environments to maintain and how to structure promotion between them.

## Decision

Three fully isolated environments: Dev, Test, and Prod.

| Environment | Subdomain | Deploy Trigger | Data | Approval Gate |
|---|---|---|---|---|
| Dev | dev.chrisbuilds64.com | Auto on push to `develop` | Synthetic | None |
| Test | test.chrisbuilds64.com | Auto on push to `release/*` | Stable dataset | None |
| Prod | api.chrisbuilds64.com | Manual after tag on `main` | Real data | Yes |

Each environment has its own database instance, its own API deployment, and its own secrets. No environment shares infrastructure with another.

**Git branching (GitFlow-light):**
```
feature/* → develop (Dev) → release/* (Test) → main (Prod) → tag v1.x.x
```

**Server distribution (tendency):** Dev and Test on one server, Prod on a dedicated server. Final decision deferred until Phase 2.

**Secrets management:** GitHub Environments with Protection Rules. `.env` files per environment, encrypted via Ansible Vault. Never committed to the repository.

## Consequences

**Benefits:**
- Defects are caught in Dev or Test before reaching Prod. The cost of finding a bug in Test is a fraction of the cost in Prod.
- The manual approval gate for Prod creates a deliberate pause. Nothing reaches production by accident.
- Synthetic data in Dev allows destructive testing without risk.
- Each environment is independently deployable and independently rollback-able.

**Trade-offs:**
- Higher infrastructure cost (multiple server instances or careful partitioning).
- More configuration to maintain (three sets of secrets, three deployment pipelines).
- Discipline required to keep environments in sync — configuration drift is a real risk.

This overhead is the point. The environment strategy is itself a demonstration of lifecycle discipline. Shortcuts here are what the reference stack is designed to avoid.
