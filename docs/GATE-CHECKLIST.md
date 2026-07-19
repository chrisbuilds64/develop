# Gate Checklist

**Status:** Active
**Date:** 2026-07-19
**Scope:** This repo. Applies before AI-generated or AI-assisted code is merged (= owned).
**Source:** Artifact type per the ChrisBuilds64 software canon. Items derived from real incidents in this repo, not invented.

The gate converts generated output into owned code. Every item is binary, specific, and owned. Maximum 5 items; updated only after an incident slips through.

| # | Check (yes/no) | Owner | Grounded in |
|---|----------------|-------|-------------|
| 1 | Every structural decision in this change (data model, API shape, module boundary, technology) is recorded as an ADR, or the change is explicitly non-structural. AI suggestions that were accepted count as decisions. | Christian | ADR-007/008/009 had to be reconstructed months later from code archaeology because this gate did not exist. |
| 2 | Behavior tests assert the spec (REQ / use case acceptance criteria), not the implementation's current output. | Christian | Software canon P3: tests generated alongside implementation are mirrors, not safety nets. |
| 3 | The changed module has a named owner (file header, README, or CODEOWNERS). "The AI wrote it" is not an owner. | Christian | Software canon P2. |
| 4 | Security surface reviewed: input validation, trust boundaries, environment-gated credentials. No secrets, tokens, or real host values in tracked files (inventory template pattern: real values only in gitignored `*.local.*`). | Christian | MockAuth reached production on an old image unnoticed until 2026-07-19; live server IP leaked into git history before the template pattern existed. |
| 5 | If the change touches deployment: config templates match server reality (diff live config against the template before running the playbook). | Christian | 2026-07-19: the Caddyfile template knew 1 of 3 live routes; an unchecked deploy would have deleted 2 production routes. |

**Test for this checklist:** would skipping any item create a liability discovered at 2am? Each item above already did, or provably would have.
