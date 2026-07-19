# UC-FE-003: PressRoom Web (Docker Deployment)

**Created:** 2026-03-15
**Last Updated:** 2026-03-15
**Type:** Frontend + Infrastructure
**Status:** ON-HOLD (was PLANNING; focus shifted to canon work)
**Owner:** Christian Moser
**Phase:** 1 (Architecture), plan approved
**Predecessor:** UC-FE-002 (PressRoom Desktop, macOS, DONE)
**Provenance:** Migrated from the private control repo and translated to English, 2026-07-19. Prior revision history remains in the control repo.

---

## Meta

**Provides:**
- PressRoom as a web app in the browser (Flutter Web)
- File API backend (FastAPI, standalone service)
- Docker package for customer self-hosting
- Server hardening playbook (VPS)

**Runtime:** Docker Compose (pressroom-web + file-api)
**Target:** pressroom.chrisbuilds64.com (own test) + customer deployments

**Relates to:**
- UC-FE-002 (PressRoom Desktop) - base app, to be refactored
- UC-BE-001 (Item API) - existing backend, pattern template
- UC-BE-003 (Auth System) - later JWT upgrade path

---

## Content Journey (Building in Public)

**This implementation is documented as a content series.**

Each phase delivers at least one article + tutorial video.

### Planned Content Pieces

| Phase | Article Idea | Track | Video |
|-------|--------------|-------|-------|
| 2 (Server) | "Server Hardening for Builders: The 15-Euro Stack Gets Serious" | DEEP TECH | Tutorial: SSH + UFW + fail2ban in 15 min |
| 2 (Server) | "Docker's Dirty Secret: Why UFW Can't Protect Your Containers" | DEEP TECH | Tutorial: Docker UFW bypass fix |
| 3.1 (File API) | "Building a File API in 200 Lines: When Less Code Means More Product" | DEEP TECH | Tutorial: FastAPI file API from scratch |
| 3.2 (Flutter) | "From Desktop to Web: The One Abstraction That Makes Flutter Portable" | DEEP TECH | Tutorial: dart:io to HTTP abstraction |
| 3.4 (Docker) | "Ship Your App in a Box: Docker Compose for Non-Technical Customers" | CLARITY | Tutorial: customer-ready Docker packaging |
| 3.5 (Deploy) | "From localhost to Production in One Session: A Builder's Deployment Story" | DEEP TECH | Tutorial: full deployment walkthrough |
| Meta | "Why I Built My Own Content Pipeline Instead of Using Notion" | CLARITY | - |

### Content Rules for This Series

- **Document honestly:** what went wrong, what surprised, what took longer
- **72-hour rule:** post frustration moments only after cooling off
- **Fix-first rule:** publish security findings only AFTER the fix
- **Tutorial format:** problem → solution → why it works → code
- **Video scripts:** teleprompter-ready, 3-5 minutes per tutorial

---

## 1. Business Understanding

**Problem:**
PressRoom runs only locally on Christian's MacBook. No customer access, no deployment test, no demonstration of build competence.

**Stakeholders:**
- Christian (own server test, content source)
- Potential customers (self-hosting package)
- Audience (tutorial content, building in public)

**Success criteria:**
- PressRoom runs as a web app on pressroom.chrisbuilds64.com
- Server is hardened (security audit passed)
- A customer can self-install with `docker compose up`
- At least 3 articles + 2 video tutorials from the journey

---

## 2. Architecture

### Service Topology

```
[Browser] → [nginx/SSL] → pressroom-web (3080) + file-api (8010)
                        → backend (8000, existing)
```

### New Components

| Component | Location | Status |
|-----------|----------|--------|
| File API | file-api/ | PLANNED |
| Flutter abstraction layer | apps/pressroom/lib/services/ | PLANNED |
| Flutter web build | apps/pressroom/Dockerfile.web | PLANNED |
| Docker Compose extension | docker-compose.yml | PLANNED |
| nginx config | deployment/pressroom.conf | PLANNED |
| Customer package | packages/pressroom-docker/ | PLANNED |

---

## 3. Implementation Phases

### Phase 2: Server Hardening
- [ ] Create deploy user + SSH key
- [ ] SSH hardening (disable root, MaxAuthTries)
- [ ] UFW review + Docker bypass fix
- [ ] Install + configure fail2ban
- [ ] Enable unattended-upgrades
- [ ] Set up backup cron
- [ ] Document security audit

### Phase 3: PressRoom Docker
- [ ] 3.1 Implement + test File API
- [ ] 3.2 Flutter abstraction layer (ContentService interface)
- [ ] 3.3 Flutter web build + Dockerfile
- [ ] 3.4 Docker Compose integration
- [ ] 3.5 DNS + nginx + SSL + deploy
- [ ] 3.6 Customer package + documentation

---

## 4. Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-15 | Separate file-api service | Customer needs no PostgreSQL, KISS |
| 2026-03-15 | Simple API key auth (v1) | No JWT overhead, upgrade path via Clerk |
| 2026-03-15 | One installation = one customer | No multi-tenant code, each deploys separately |
| 2026-03-15 | Content series parallel to implementation | Building in public, demonstrate competence |
