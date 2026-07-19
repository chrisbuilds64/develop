# UC-BE-003: Authentication System

**Created:** 2026-01-22
**Last Updated:** 2026-04-15
**Status:** DEPLOYED v1 (MockAuth); v2 (JWT/Clerk) planned
**Owner:** Christian
**Provenance:** Migrated from the private control repo and translated to English, 2026-07-19. Prior revision history remains in the control repo.

---

## 1. Business Understanding

**Problem:**
Secure authentication for API access. Different clients (web, mobile, CLI) need to identify themselves.

**Stakeholders:**
- Chris (developer, admin)
- Future users (multi-tenant)
- Frontends (web, mobile, CLI)

**Success criteria:**
- Token-based auth works
- Adapter pattern enables provider switching
- No security vulnerabilities

**Scope:**
- IN: Token verification, user identity, adapter pattern
- OUT: OAuth/social login (later), user registration UI

---

## 2. Data Understanding

**User data:**
- user_id (unique identifier)
- email
- name

**Token data:**
- v1: simple string tokens (mock)
- v2: JWT with claims (exp, iat, sub)

**Gaps:**
- No user store (v1 uses hardcoded test users)
- No token expiration (v1)

---

## 3. Data Preparation

**v1 (current):**
- [x] UserInfo dataclass defined
- [x] Test users hardcoded (chris, lars, lily)

**v2 (planned):**
- [ ] User table in PostgreSQL
- [ ] Password hashing (argon2/bcrypt)
- [ ] Refresh token storage

---

## 4. Modeling

### v1 Architecture (DONE)

```
adapters/auth/
├── __init__.py      # Exports
├── base.py          # AuthProvider ABC, UserInfo dataclass
├── exceptions.py    # AuthenticationError
└── mock_adapter.py  # MockAuthAdapter for dev/test
```

**Pattern:** Adapter pattern (strategy)
- `AuthProvider` interface: `verify_token(token) -> UserInfo`
- Implementations swappable without API changes

**Test users (v1):**
| Token | User |
|-------|------|
| test-chris | Chris (default) |
| test-lars | Lars |
| test-lily | Lily |
| any other | Chris (fallback) |
| empty/"invalid" | AuthenticationError |

### v2 Options (TBD)

| Option | Pro | Con |
|--------|-----|-----|
| **Self-built JWT** | Full control, no vendor | More work, security risk |
| **Clerk** | Fast, managed, UI included | Cost, vendor lock-in |
| **SuperTokens** | Self-hosting possible, OSS | More setup |
| **Auth0** | Enterprise-ready | Expensive at scale |

**Tendency:** self-built JWT for the backend, possibly Clerk for the frontend later

---

## 5. Evaluation

**v1 metrics:**
- [x] Mock auth works in dev
- [x] API endpoints protected
- [x] Adapter swappable

**v2 acceptance criteria:**
- [ ] JWT generation + verification
- [ ] Token expiration (access: 15min, refresh: 7d)
- [ ] Secure password storage
- [ ] Rate limiting on login

---

## 6. Deployment

**v1 (current):**
- MockAuthAdapter active in development
- No production deployment (mock only); production ENV fails closed, see `docs/adr/ADR-008-mockauth-environment-guard.md`

**v2 plan:**
- Implement JWT adapter
- Environment-based provider selection
- Secrets via environment variables

**Monitoring:**
- Log failed auth attempts
- Track rate limit violations

---

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Jan 2026 | Adapter pattern | Flexibility for provider switching |
| Jan 2026 | Mock for v1 | Fast dev start, real auth later |
| Jan 2026 | UserInfo dataclass | Standardized user representation |

---

## Status Updates

| Date | Phase | Status | Notes |
|------|-------|--------|-------|
| Jan 2026 | Modeling | v1 Complete | MockAuthAdapter functional |
| 2026-01-22 | Documentation | Retroactive | Use case written after the fact |

---

## Related

- Code: `services/backend/adapters/auth/`
- API integration: `services/backend/api/dependencies.py`
- Decisions: `docs/adr/ADR-008-mockauth-environment-guard.md`

---

## Next Steps (v2)

1. [ ] Decision: self-built JWT vs. Clerk vs. SuperTokens
2. [ ] User table + migration
3. [ ] Implement password hashing
4. [ ] Write JWT adapter
5. [ ] Refresh token flow
6. [ ] Login/register endpoints
