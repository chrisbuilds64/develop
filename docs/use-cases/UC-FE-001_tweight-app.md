# UC-FE-001: tweight App

**Created:** 2026-01-22
**Last Updated:** 2026-04-15
**Status:** IN PROGRESS (Phase 4, prototype to product transition)
**Owner:** Christian
**Provenance:** Migrated from the private control repo and translated to English, 2026-07-19. Prior revision history remains in the control repo.

---

## 1. Business Understanding

**Problem:**
Brain dump without friction. Capture thoughts, tasks, and ideas fast, without app overhead.

**Value proposition:**
> "tweight - Focus on the 20% that matters" (twenty + eighty = tweight)

**Stakeholders:**
- Chris (primary user, developer)
- Future users (pitch target)

**Success criteria:**
- Pitch-ready product
- Daily driver for Chris
- < 3 seconds from app open to capture

**Scope:**
- IN: Quick capture, items, tags, search, sync
- OUT: AI features, team collaboration, complex project management

---

## 2. Data Understanding

**Data model:**
- Items (label, content_type, payload, tags)
- Tags (name, color?)
- User (auth via backend)

**Backend integration:**
- API: `api.chrisbuilds64.com`
- Auth: token-based (UC-BE-003)
- Items: CRUD via UC-BE-001

**Gaps:**
- Offline-first not yet implemented
- Tag management API missing in backend

---

## 3. Data Preparation

**Current state:**
- [x] Flutter project setup
- [x] Basic auth flow (login screen)
- [x] API client structure
- [ ] Full item CRUD UI
- [ ] Tag system UI
- [ ] Search implementation

**Data flow:**
```
App → API Client → Backend API → PostgreSQL
                ↓
           Local Cache (later)
```

---

## 4. Modeling

**Tech stack:**
- Flutter (cross-platform)
- Dart
- HTTP package (API)
- SharedPreferences (token storage)

**Architecture:**
```
lib/
├── main.dart
├── config.dart
├── models/          # Data models
├── services/        # API integration
├── screens/         # UI screens
└── widgets/         # Reusable components
```

**Design principles:**
- KISS, minimal dependencies
- No state management library (v1)
- Clean separation: Screen → Service → API

---

## 5. Evaluation

**Pitch-ready criteria:**
- [ ] Core flow works (capture → view → organize)
- [ ] Visually polished
- [ ] Reliable (no crashes)
- [ ] Demo video possible

**Technical metrics:**
- App start < 2s
- Capture < 3s (open to saved)
- Sync reliable

---

## 6. Deployment

**Platforms:**
- Phase 1: iOS (TestFlight)
- Phase 2: Android (internal testing)
- Phase 3: Public release

**Current:**
- Local development
- Connects to production API

---

## Feature Roadmap

| Feature | Status | Priority |
|---------|--------|----------|
| Login/Auth | Done | - |
| Item list view | In Progress | P1 |
| Create item | In Progress | P1 |
| Edit item | Pending | P1 |
| Delete item | Pending | P1 |
| Quick capture (multi-line) | Pending | P1 |
| Tag filter | Pending | P2 |
| Search | Pending | P2 |
| Card vs. text view toggle | Pending | P2 |
| Offline mode | Pending | P3 |
| Dark mode | Pending | P3 |

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Jan 2026 | Flutter over native | Cross-platform, faster |
| Jan 2026 | No state mgmt library | KISS, v1 simple enough |
| Jan 2026 | Prototype → product | Goal: pitch-ready |

---

## Status Updates

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| 2026-01-20 | Setup | Done | Project created |
| 2026-01-21 | Modeling | Vibe coding | Auth + basic structure |
| 2026-01-22 | Documentation | Use case written | Transition to structured |

---

## Related

- Code: `apps/tweight/`
- Requirements: `docs/requirements/REQ-002-tweight-App.md`
- Backend: UC-BE-001 (items), UC-BE-003 (auth)

---

## Development Mode

**Hybrid approach:**
- **Feature work** → CRISP, documented
- **UI exploration** → vibe coding, timeboxed
- **Bug fixes** → direct, session log is enough

**Rule:** Add every new feature to the feature roadmap before building it.
