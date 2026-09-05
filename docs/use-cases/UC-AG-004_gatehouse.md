# UC-AG-004: Gatehouse — Canon Elicitation Harness

**Created:** 2026-08-22
**Type:** Agent
**Status:** IN PROGRESS (corrected 2026-09-05 from DRAFT — running code, ADR-011 and ADR-012, one real run and one demo run behind it)
**Owner:** Christian Moser
**Phase:** 4 (Modeling) — corrected 2026-09-05, to be confirmed by Chris

---

## Meta

**Provides:**
- `POST /api/v1/session` - Start an elicitation run against a configured canon pack
- `GET  /api/v1/session/{id}` - Current block, question, and answers so far
- `POST /api/v1/session/{id}/answer` - Submit an answer, receive follow-up questions
- `POST /api/v1/session/{id}/close-block` - Close a block against its exit criteria
- `GET  /api/v1/session/{id}/artifacts` - Rendered artifacts produced by the run
- `GET  /api/v1/audit` - What was sent to the model, when, and how much

**Consumes:**
- Canon pack (external directory, not shipped with the code)
- One model endpoint via the adapter defined in ADR-011

---

## Dependencies

| UC | Name | Required | Status |
|----|------|----------|--------|
| — | — | — | — |

Gatehouse has no dependency on the existing backend (UC-BE-001/003). It runs as a standalone process on client hardware.

---

## 1. Business Understanding

**Problem:**

Client systems are grown, not governed. Structure exists but is undocumented, lives in people's heads, and cannot be audited. Establishing a canon at a client currently requires a consultant in a chat window with a general-purpose model. That is not repeatable, not installable, and it gives the client no control over what leaves the building.

Three things are missing:

1. A repeatable procedure that produces the same quality of interview regardless of who runs it.
2. A place where the resulting canon lives at the client, under version control, that outlives the engagement.
3. Control and evidence over what content is sent to a model, and the freedom to choose which model that is.

**Stakeholders:**

- Client: gets a canon they own, in their own version control, plus a record of what left their network.
- Client IT / data protection: gets model choice (own subscription, own tenant, or on-premise) and an audit trail.
- ChrisBuilds64: gets a repeatable delivery instead of a bespoke conversation.

**Success Criterion:**

One complete run against `develop/` produces a canon draft without a chat window, using real answers, in under 90 minutes, with a complete audit record of every model call.

Secondary: a second run against a different domain uses the same binary and a different canon pack, with no code change.

**Scope:**

- IN: guided elicitation across the canon pack's blocks; model-driven follow-up questions; answers persisted as files in a client instance directory; artifact rendering; audit log of model traffic; pluggable model adapter; single-user local operation.
- OUT: analysis of client files, code, or history (that is a separate stage with a different risk profile); gates and approval workflows; multi-user and authentication; cost display; packaging and installer; the canon pack content itself, which stays private IP.

---

## 2. Data Understanding

**Available Data:**

- Canon pack: the question blocks, stage directions, follow-up triggers, and exit criteria. Read-only input, supplied at startup as a directory path.
- Client answers: free text typed by a human during the run. This is the only client data Gatehouse handles at this stage.

**Data Quality:**

- Completeness: enforced per block by exit criteria, not by field validation.
- Currency: each run is a point-in-time snapshot; the instance directory is versioned so drift is visible.
- Consistency: answers are marked `[AS-IS]`, `[PROPOSED]`, or `[OPEN]` so a draft is never mistaken for a description of reality.

**Gaps:**

The canon pack v0.1 elicits what should exist. It does not yet systematically elicit what already exists at the client and what of it should be kept. Brownfield is the normal case, not the exception. Closing this gap is the primary finding expected from the first real run.

---

## 3. Data Preparation

**Transformations:**

- [ ] Answer text → block record in the instance directory
- [ ] Block records → interview document
- [ ] Interview document → findings document
- [ ] Findings → canon draft artifact

**Pipeline:**

```
[canon pack] → [block runner] → [model adapter] → [follow-up]
                     ↓
              [instance files] → [artifact renderer] → [UI view]
                     ↓
              [audit log]
```

---

## 4. Modeling

**Approach:**

A single local process serving a browser UI. Three separations carry the design:

- **Core vs. instance.** The code contains no questions. The canon pack is loaded from a configured path at startup. The public code is inoperable without the private pack, which enforces the separation rather than merely asserting it.
- **Elicitation vs. execution.** Gatehouse asks and records. It does not read, scan, or modify the client system.
- **Harness vs. model.** All model traffic passes one adapter interface (ADR-011).

**Rationale:**

The core/instance split is what makes the product licensable and the canon portable. It also makes the three-domain test a matter of three packs rather than three builds.

**Technology:**

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Runtime | Python 3.11+, FastAPI | Matches existing stack and operator skill; single process |
| Storage | Files on disk, under client version control | Portable, auditable, survives the engagement (ADR-010) |
| UI | Server-rendered HTML, minimal JS, no build step | Nothing to compile means nothing to install (ADR-010) |
| Model access | Adapter interface, configured endpoint | Client keeps model choice and data residency (ADR-011) |

---

## 5. Evaluation

**Metrics:**

- Technical: a full pack traversal completes without manual file editing; every model call appears in the audit log; a second pack runs with no code change.
- Business: time from start to canon draft; number of follow-up questions the operator had to invent by hand (target: zero).

**Acceptance Criteria:**

- [ ] A run traverses all blocks of a pack and closes each against its exit criteria
- [ ] Answers persist as files in the instance directory and survive a process restart
- [ ] Artifacts are viewable in the UI without opening a file manager
- [ ] The audit log records every model call: timestamp, endpoint, content sent, tokens
- [ ] Swapping the configured model endpoint requires no code change
- [ ] Starting with no canon pack configured fails with a clear message, not a stack trace

**Test Plan:**

| Test | Type | Covered |
|------|------|---------|
| Pack loader rejects a malformed pack | Unit | [ ] |
| Block runner enforces exit criteria | Unit | [ ] |
| Adapter contract holds across two implementations | Integration | [ ] |
| Audit log captures every outbound call | Integration | [ ] |
| Full run against `develop/` | E2E | [ ] |

---

## 6. Deployment

**Environment:**

| Env | URL | Config |
|-----|-----|--------|
| Local | localhost:8100 | `gatehouse.toml` |
| Client site | localhost on client hardware | `gatehouse.toml` at client |

Gatehouse is not deployed to ChrisBuilds64 production infrastructure. It runs where the client's data is.

**Rollout:**

- [ ] Local run against `develop/` verified
- [ ] Packaging decided (container or single executable) — deferred until a real client is scheduled

**Monitoring:**

The audit log is the operational record. There is no telemetry back to ChrisBuilds64; a client-side product that phones home would contradict its own premise.

**Rollback:**

The instance directory is under version control. Any run can be reverted; the code holds no state.

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-22 | Name: Gatehouse | The controlled passage in a wall: the rule is kept there and what passes is recorded. Sits in the existing castle metaphor |
| 2026-08-22 | Stage 1 excludes file analysis | Interview is data-poor, system analysis is data-rich. Different risk profile, different stage |
| 2026-08-22 | Canon pack is not shipped with the code | Core/instance separation enforced by construction; the pack is the licensed IP |
| 2026-08-22 | No database | See ADR-010 |

---

## Status Updates

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| 2026-08-22 | 1 | DRAFT | Use case created; ADR-010 and ADR-011 recorded |

---

## Related

- **Code:** `develop/apps/gatehouse/`
- **ADR:** ADR-010 (runtime and storage), ADR-011 (model adapter)
- **Sessions:** `2026-08-22_*.md`
