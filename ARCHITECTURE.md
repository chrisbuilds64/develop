# ChrisBuilds64 - Architecture & Vision

**Last Updated:** January 4, 2026
**Status:** Building in Public
**Philosophy:** KISS, YAGNI, Use Case Driven

---

## 📚 Related Documents

- [/control/CLAUDE.md](/control/CLAUDE.md) - Unchanging principles (Private)
- [/control/PROJECT-CONTEXT.md](/control/PROJECT-CONTEXT.md) - Current project state (Private)
- [SECURITY.md](SECURITY.md) - Security guidelines & threat analysis
- [README.md](README.md) - Public project overview

**Note:** Links to `/control/` are for internal reference only. Control directory is private.

---

## 🎯 The Vision

**Core provides everything a developer needs to build applications on this structure.**

Not the "eierlegende Wollmilchsau" (jack-of-all-trades), but essential functionality that enables rapid application development.

We won't build everything ourselves. Where good solutions exist, we'll build adapters—but those adapters become part of Core.

**Goal:** Use Cases on the application side can be implemented very quickly, like our YouTube Link Manager app.

---

## 🏗️ Architecture Overview

```
ChrisBuilds64/
├── control/                    # Strategic Engine (Private)
│   ├── PROJECT-CONTEXT.md      # Current project state
│   ├── CLAUDE.md               # AI collaboration principles
│   ├── TODO-LIST.md            # Work status
│   └── integrations/           # WAL, external systems
│
├── develop/                    # Development (Public - Building in Public)
│   ├── core/                   # Abstract, reusable services
│   │   ├── usecases/           # Core use cases (RAG, Docker, etc.)
│   │   ├── main.py             # FastAPI backend
│   │   ├── models.py           # Abstract models (Item, Work, etc.)
│   │   ├── Dockerfile          # Containerization
│   │   └── ...
│   │
│   ├── tweight/                # Application Group: Productivity
│   │   ├── usecases/           # Tweight-specific use cases
│   │   ├── lib/                # Flutter app code
│   │   └── ...
│   │
│   └── [future-app-groups]/    # e.g., patient records, archive system
│
└── brand/                      # Content (Public - Building in Public)
    ├── content/posts/          # Daily posts (DAY-XXX)
    └── content/books/          # Published books
```

---

## 📦 Component Breakdown

### Control (Private Repo)

**Purpose:** Strategic engine for Chris + AI collaboration

**Contains:**
- `PROJECT-CONTEXT.md` - Running context of all projects
- `CLAUDE.md` - Unchanging principles for AI-assisted development
- `TODO-LIST.md` - Current work status
- Integration configs (WAL, external systems)

**Why Private:**
- Building in Public = show results, not every internal decision
- Strategic thinking remains confidential
- The world can see what we build, not how we plan

**Git:** Private repository

---

### Core (Public - Building in Public)

**Purpose:** Abstract, reusable services that power all applications

**Examples:**
- Item Manager (abstract CRUD for any content type)
- Work Manager (task/workflow orchestration)
- RAG System (knowledge retrieval)
- Docker Infrastructure (deployment)
- **Authentication/Authorization** (UC-003 - IMPLEMENTED ✅)
- Workflow Engine (future)

**Principles:**
- Abstract, not application-specific
- Reusable across multiple app groups
- Well-documented for other developers
- Adapters for existing tools (don't reinvent the wheel)

**Use Cases:**
- `/develop/core/usecases/UC-002-personal-knowledge-rag.md`
- `/develop/core/usecases/UC-003-...` (future)

**Git:** Public repository (Building in Public)

---

### Tweight (Public - Building in Public)

**Purpose:** Application Group for Productivity Tools

**Based on:** Core's abstract models and services

**Examples:**
- YouTube Link Manager (UC-001)
- Workout Timer (future)
- Note Manager (future)
- To-Do System (future)

**Architecture:**
- Flutter app (cross-platform)
- Consumes Core APIs
- Fast to build (thanks to Core abstraction)

**Use Cases:**
- `/develop/tweight/usecases/UC-001-youtube-link-manager.md`
- `/develop/tweight/usecases/UC-004-...` (future)

**Git:** Public repository (Building in Public)

---

### Other Application Groups (Future)

**Examples:**
- Patient Records System
- Archive & Documentation System
- [Your idea here]

**Based on:** Same Core as Tweight

**Why This Works:**
- Core provides Item Manager → any app can manage items (videos, patients, documents)
- Core provides Work Manager → any app can orchestrate workflows
- Core provides RAG → any app can query knowledge
- Rapid development of new apps

---

## 🧭 Guiding Principles

### 1. KISS (Keep It Simple, Stupid)
- Simple solutions over complex architectures
- Ship working code over perfect design
- Refactor when needed, not in advance

### 2. YAGNI (You Ain't Gonna Need It)
- Build for today's problem
- Don't abstract until you have 2+ concrete examples
- Vision documented ≠ Vision implemented

### 3. Use Case Driven
- Every feature starts with a Use Case (UC-XXX)
- Concrete problem → Concrete solution
- Abstract models emerge from concrete use cases

### 4. Building in Public
- Code is public (develop/, brand/)
- Strategy is private (control/)
- Show results, share learnings, don't expose every decision

### 5. Concrete > Abstract
- YouTube Link Manager first
- Abstract Item Manager second (when we have 2+ concrete examples)
- Premature abstraction = scope creep

---

## 🔄 Development Workflow

### Use Case Format:
- **UC-XXX-descriptive-name.md**
- Numbered sequentially across all projects
- Stored in project-specific `/usecases/` folder
- Format: Problem → Solution → Success Criteria → What We're NOT Building

### Example:
- `UC-001` (Tweight): YouTube Link Manager
- `UC-002` (Core): Personal Knowledge RAG
- `UC-003` (Core): Docker Deployment (could be retroactive documentation)
- `UC-004` (Tweight): Workout Timer

### No Prefix Chaos:
- ❌ UC-B001, UC-A001 (too complex)
- ✅ UC-001, UC-002, UC-003 (simple, sequential)

---

## 🛠️ Technology Stack

### Core (Backend/Services)
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Database:** SQLite (can migrate to PostgreSQL when needed)
- **Containerization:** Docker, docker-compose
- **Deployment:** Strato VPS (Ubuntu 24.04 LTS)
- **Reverse Proxy:** nginx
- **SSL:** Let's Encrypt (certbot)

### Tweight (Flutter App)
- **Framework:** Flutter (Dart)
- **Platforms:** iOS, Android (Linux/Mac/Windows future)
- **State Management:** Provider (simple, KISS)
- **HTTP Client:** http package
- **Deployment:** App Store, Google Play (TestFlight for beta)

### RAG (Core Service)
- **Vector DB:** Qdrant
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **LLM API:** Claude API (for chatbot, optional)

### Infrastructure
- **Server:** Strato VPS VC8-32 (8 vCores, 32GB RAM)
- **DNS:** Managed by Alex (deinocheirus.hostingschmiede.de)
- **Domain:** api.chrisbuilds64.com (production API)

---

## 📊 Current Status

### Shipped (Day 1-8):
- ✅ UC-001: YouTube Link Manager (Tweight)
- ✅ Core API deployed to production (api.chrisbuilds64.com)
- ✅ Docker containerization with nginx reverse proxy
- ✅ SSL certificate setup (Let's Encrypt, auto-renewal)
- ✅ Flutter app on iPhone (production API)
- ✅ Website deployed: chrisbuilds64.com (HTTPS)
- ✅ Security documentation & hardening script
- ✅ Content principles formalized
- ✅ 8 days of content published (DAY-001 to DAY-008)

### In Progress:
- ⏳ Social media posting (Day 7 & 8)
- ⏳ Publishing Day 7 & 8 to Substack

### Planned:
- 📋 Security hardening execution (run security-hardening.sh)
- 📋 TestFlight beta deployment (Tweight)
- 📋 UC-002: Personal Knowledge RAG (Core)
- 📋 More Tweight modules (UC-004+)

---

## 🚀 Why This Architecture Works

### Speed:
- Core provides building blocks
- Apps assemble blocks into features
- Rapid prototyping (UC-001 in one afternoon)

### Flexibility:
- Core is abstract, apps are concrete
- Add new app groups without touching Core
- Core improvements benefit all apps

### Transparency:
- Building in Public = code visible
- Control = strategy private
- Best of both worlds

### Sustainability:
- KISS prevents over-engineering
- YAGNI prevents scope creep
- Use Case Driven ensures real value

---

## 🎯 Testing the Vision

**We will test the functionality of this vision by rapidly developing several useful apps for Tweight very soon.**

If Core truly provides the building blocks we claim, new Tweight modules should be quick to build.

If it's hard, we're over-abstracting or missing essential pieces.

**The proof is in the shipping.**

---

## 🌍 Building in Public

This document is public. The world can see:
- Our architecture
- Our principles
- Our code

The world cannot see:
- `/control/` (private repo)
- Internal planning docs
- Strategic decisions before they're implemented

**Why?**
- Transparency builds trust
- Sharing knowledge helps others
- Privacy protects focus

---

## 📚 Resources

- **GitHub:** https://github.com/chrisbuilds64
- **Substack:** https://chrisbuilds64.substack.com
- **Website:** https://chrisbuilds64.com
- **API:** https://api.chrisbuilds64.com/health

---

**Last Updated:** January 1, 2026
**Next Review:** After UC-002 shipped or 3 new Tweight modules

---

*Building in public. Solving real problems. Shipping when ready.* 🚀
