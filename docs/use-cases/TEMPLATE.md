# UC-{TYPE}-{NNN}: {Title}

**Created:** [Date]
**Type:** Backend | Frontend
**Status:** DRAFT | IN PROGRESS | BLOCKED | REVIEW | DEPLOYED | ARCHIVED
**Owner:** [Name]
**Phase:** 1-6 (Business Understanding → Deployment)

---

## Meta

**Provides:** (Backend only)
- `POST /api/v1/...` - Description
- `GET /api/v1/...` - Description

**Consumes:** (Frontend only)
- `UC-BE-XXX` - Endpoint needed

---

## Dependencies

| UC | Name | Required | Status |
|----|------|----------|--------|
| UC-BE-XXX | [Name] | [Endpoint/Feature] | [Status] |

**Blocked:** [If blocked: reason and waiting for what]
**Unblocked:** [Date + what resolved it]

---

## 1. Business Understanding

**Problem:**
What is the concrete business problem?

**Stakeholders:**
Who benefits? Who is affected?

**Success Criterion:**
How do we measure success? (quantifiable)

**Scope:**
- IN: [What is included]
- OUT: [What is explicitly excluded]

---

## 2. Data Understanding

**Available Data:**
- Source 1: [Description, format, access]
- Source 2: ...

**Data Quality:**
- Completeness: [Assessment]
- Currency: [Assessment]
- Consistency: [Assessment]

**Gaps:**
What is missing? What needs to be acquired?

---

## 3. Data Preparation

**Transformations:**
- [ ] Transformation 1
- [ ] Transformation 2

**Feature Engineering:** (if applicable)
Which features are needed?

**Pipeline:**
```
[Input] → [Process] → [Output]
```

---

## 4. Modeling

**Approach:**
Which solution/architecture?

**Rationale:**
Why this approach and not alternative X?

**Technology:**
| Component | Choice | Rationale |
|-----------|--------|-----------|
| [Component] | [Choice] | [Why] |

**API Design:** (Backend only)
```
POST /api/v1/...
  Request: { ... }
  Response: { ... }
```

**UI Components:** (Frontend only)
- Screen/Widget 1
- Screen/Widget 2

---

## 5. Evaluation

**Metrics:**
- Technical: [e.g. latency, accuracy, test coverage]
- Business: [e.g. user satisfaction, time saved]

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

**Test Plan:**
| Test | Type | Covered |
|------|------|---------|
| [Description] | Unit/Integration/E2E | [ ] |

---

## 6. Deployment

**Environment:**
| Env | URL | Config |
|-----|-----|--------|
| Local | localhost:8000 | .env.local |
| Production | api.chrisbuilds64.com | .env.prod |

**Rollout:**
- [ ] Local verified
- [ ] Staging tested
- [ ] Production deployed

**Monitoring:**
What is monitored? Alerts?

**Rollback:**
Plan if things go wrong?

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| [Date] | [Decision] | [Why] |

---

## Status Updates

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| [Date] | [1-6] | [Status] | [What happened] |

---

## Related

- **Code:** `develop/services/backend/...` or `develop/apps/...`
- **Sessions:** `2026-XX-XX_*.md`
- **Depends on:** UC-BE-XXX, UC-FE-XXX
- **Blocks:** UC-FE-XXX
