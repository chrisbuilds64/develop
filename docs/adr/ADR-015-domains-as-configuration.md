# ADR-015: Domains Are Configuration, Not Code

**Status:** Proposed
**Date:** 2026-10-21

---

## Context

The same case engine is meant to carry more than one domain: a content pipeline today, a claims file next. Each has its own stages, deliverables, words, approval rules and agent tasks.

## Decision

- Engine code never names a domain. Stages (`stages.json`: folder, label, whose turn, actions, required deliverables, conditions such as four-eyes or an amount field), deliverables (`artifacts.json`, extended with `shape` and `required`), words (`vocabulary.json`) and theme (`theme.json`) are files per domain.
- Every case records `configVersion` in `meta.json`. A rename of a stage or deliverable ships with a mapping so older cases keep rendering.
- No generic pack format yet. It is extracted from the real differences once a second domain runs in production.

## Alternatives

- **A full domain-pack format designed up front:** premature while only one domain is in production.
- **Hard-coding the second domain:** would fork the engine.

## Consequences

- A demo domain with fictional data is a copy of configuration files, not a branch of code.
