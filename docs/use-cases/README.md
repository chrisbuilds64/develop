# Use Case Process (CRISP-DM)

**Created:** 2026-01-25
**Status:** Binding
**Owner:** Christian Moser
**Provenance:** Migrated from the private control repo and translated to English, 2026-07-19.

---

## 1. Use Case Types

### UC-BE-XXX: Backend Use Cases
**Scope:** service layer, API endpoints, data processing, business logic

**Characteristics:**
- Runs on the server (Docker)
- Provides API endpoints
- Processes data
- Has no UI

**Examples:**
- RAG Knowledge API
- Auth Service
- Item CRUD API

### UC-FE-XXX: Frontend Use Cases
**Scope:** user interface, user experience, client-side logic

**Characteristics:**
- Runs on the client (Flutter app, web)
- Consumes backend APIs
- Has UI components
- User interaction

**Examples:**
- Search UI in tweight
- Weight entry screen
- Dashboard view

### UC-AG-XXX: Agent Use Cases
**Scope:** autonomous AI agents, automation, scheduled tasks, messaging

**Characteristics:**
- Runs as a daemon (24/7, local or remote)
- Messaging-based (Telegram, WhatsApp, Discord, etc.)
- Autonomous or cron-triggered
- Reads/processes local data
- No classic UI, the channel is the interface

**Examples:**
- Morning briefing via Telegram
- Content pipeline automation
- Engagement monitoring

---

## 2. Naming Convention

**Format:** `UC-{TYPE}-{NNN}_{slug}.md`

| Part | Meaning | Example |
|------|---------|---------|
| UC | Use case prefix | UC |
| TYPE | BE (backend), FE (frontend), AG (agent) | BE |
| NNN | 3-digit number | 002 |
| slug | kebab-case description | rag-knowledge |

**Examples:**
- `UC-BE-001_item-api.md`
- `UC-BE-002_rag-knowledge.md`
- `UC-FE-001_tweight-app.md`

**Numbering:**
- BE, FE, and AG have separate number ranges
- Starts at 001
- Sequential, never fill gaps

---

## 3. Dependency Model

### Rule: Frontend waits for backend

```
UC-FE-002: Search UI
├── Status: BLOCKED
├── Blocked by: UC-BE-002 (RAG Knowledge API)
├── Requires: GET /api/v1/rag/query
└── Unblocked when: UC-BE-002 reaches Phase 6 (Deployment)

UC-BE-002: RAG Knowledge API
├── Status: IN PROGRESS
├── Phase: 4 (Modeling)
├── Provides: /api/v1/rag/query, /api/v1/rag/status
└── Consumers: UC-FE-002
```

### Status Values

| Status | Meaning |
|--------|---------|
| DRAFT | Initial draft, not started |
| IN PROGRESS | Actively being worked on |
| BLOCKED | Waiting on a dependency |
| REVIEW | Done, waiting for acceptance |
| DEPLOYED | In production |
| ARCHIVED | Completed or abandoned |

### Blocking Rules

1. **FE needs a BE endpoint that doesn't exist:**
   - FE use case → status: BLOCKED
   - Create a BE use case for the missing endpoint
   - FE references: `Blocked by: UC-BE-XXX`

2. **BE use case reaches deployment:**
   - All dependent FE use cases → status: UNBLOCKED
   - FE work can continue

3. **Circular dependencies:**
   - NOT ALLOWED
   - Requires an architecture redesign

---

## 4. CRISP-DM Phases

### Phase 1: Business Understanding
**Questions:**
- What is the problem?
- Who benefits?
- What does success look like?
- What is IN/OUT of scope?

**Output:** problem statement, success criteria, scope definition

### Phase 2: Data Understanding
**Questions:**
- What data exists?
- What is its quality?
- What is missing?

**Output:** data inventory, quality assessment, gap analysis

### Phase 3: Data Preparation
**Questions:**
- Which transformations?
- How does the data flow?

**Output:** ETL pipeline, data schema

### Phase 4: Modeling
**Questions:**
- Which architecture?
- Which technology?
- Why this approach?

**Output:** architecture decision, tech stack, API design

### Phase 5: Evaluation
**Questions:**
- How do we test?
- What are the acceptance criteria?

**Output:** test plan, acceptance criteria

### Phase 6: Deployment
**Questions:**
- How is it deployed?
- How do we monitor?
- What is the rollback plan?

**Output:** deployment script, monitoring setup, runbook

---

## 5. When to Create a Use Case

### YES, create a use case:
- Feature goes to production
- Spans multiple sessions
- Architecture decisions needed
- Has dependencies on other use cases
- Backend API endpoint

### NO use case:
- Quick fix / bug fix
- Styling / UI polish
- Refactoring without feature change
- One-off tasks

### Grey area, decision aid:
- Takes more than 2 sessions? → UC
- Needs new API endpoints? → UC
- Affects other features? → UC

---

## 6. Use Case Lifecycle

```
1. DRAFT
   └── Start business understanding
        └── Problem clear? → move to IN PROGRESS

2. IN PROGRESS
   └── Work through the CRISP phases
   └── On dependency → BLOCKED
        └── Dependency resolved → back to IN PROGRESS

3. BLOCKED
   └── Waiting on a dependency (UC-BE-XXX)
   └── No active work
        └── Dependency deployed → UNBLOCKED → IN PROGRESS

4. REVIEW
   └── All phases done
   └── Deployment prepared
        └── Approved → DEPLOYED

5. DEPLOYED
   └── In production
   └── Monitoring active
        └── Project complete → ARCHIVED

6. ARCHIVED
   └── Historical
   └── Read-only
```

---

## 7. Template Updates on Status Change

**On BLOCKED:**
```markdown
## Dependencies

| UC | Name | Required | Status |
|----|------|----------|--------|
| UC-BE-002 | RAG API | /api/v1/rag/query | IN PROGRESS |

**Blocked:** Waiting for UC-BE-002 to reach Deployment.
```

**On UNBLOCKED:**
```markdown
## Dependencies

| UC | Name | Required | Status |
|----|------|----------|--------|
| UC-BE-002 | RAG API | /api/v1/rag/query | DEPLOYED |

**Unblocked:** 2026-01-25 - dependency deployed.
```

---

## 8. Relationship to Other Artifact Types

A use case is the container for a feature or system. This CRISP-DM process is the battle-tested instance of the canonical "Use Case" artifact type (ChrisBuilds64 software canon v0.2); the canon carries the abstract phase structure, this document the method-specific expression.

Related artifact types in `docs/`:

```
Use Case (why + what, CRISP-DM container)
   └── REQ-XXX (detailed specification)      → docs/requirements/
   └── ADR-XXX (architecture decisions)      → docs/adr/
   └── Code                                  → services/, apps/, infra/
   └── Runbook (operations)                  → docs/runbooks/
```

---

**Document status:** binding since 2026-01-25. Agent use cases (UC-AG-XXX) that do not describe software in this repo live outside it.
