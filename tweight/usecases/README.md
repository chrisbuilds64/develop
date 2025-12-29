# Tweight - Use Cases

**Purpose:** Organize feature development, user stories, and implementation plans

**Approach:** KISS - Simple markdown files, one use case per feature, numbering for tracking

---

## 📁 Structure

```
usecases/
├── README.md                           # This file
├── UC-001-youtube-link-manager.md      # Use Case documentation
├── UC-001-implementation.md            # Implementation guide
├── UC-002-[next-feature].md            # Next use case
└── ...
```

**Naming Convention:**
- `UC-XXX-feature-name.md` = Use case documentation
- `UC-XXX-implementation.md` = Implementation guide (optional)

---

## 📋 Active Use Cases

### UC-001: YouTube Link Manager
**Status:** 🔄 In Progress (Dec 29, 2025)
**Goal:** Save YouTube links with tags, filter and view
**Files:**
- [UC-001-youtube-link-manager.md](UC-001-youtube-link-manager.md)
- [UC-001-implementation.md](UC-001-implementation.md)

**User Story:**
As a user, I want to save YouTube videos with custom tags so that I can easily find and watch them later.

**Priority:** High (Real need, simple scope)
**Complexity:** Simple
**Timeline:** 1 day

---

## 📝 Backlog (Future Use Cases)

### UC-002: To-Do Management (Future)
**Status:** 💡 Idea
**Goal:** Manage tasks with Pareto Principle (20% that matters)
**Priority:** High (Core Tweight concept)
**Dependencies:** UC-001 (learn from implementation)
**Notes:** May require refactoring to generic Item system

---

### UC-003: Generic Item System (Future)
**Status:** 💡 Idea (After 2+ concrete use cases)
**Goal:** Abstract backend to handle multiple content types
**Priority:** Medium
**Dependencies:** UC-001 + UC-002 (need real data to design abstraction)
**Notes:** Architectural refactoring, not user-facing feature

---

## 🎯 Use Case Template

When creating new use case, copy this template:

```markdown
# UC-XXX: [Feature Name]

**Created:** YYYY-MM-DD
**Status:** 💡 Idea / 🔄 In Progress / ✅ Completed
**Priority:** High / Medium / Low

---

## 🎯 Goal

[One sentence: What problem does this solve?]

---

## 🚫 What This Is NOT

[What we're NOT building - scope control]

---

## 📱 User Stories

### Story 1: [Title]
**As a** [user type]
**I want** [action]
**So that** [benefit]

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

---

## 🗄️ Database Schema

[Tables, fields, relationships]

---

## 🔌 API Endpoints

[Endpoints needed]

---

## 📱 Frontend

[Screens, components, user flow]

---

## ✅ Success Criteria

[How do we know it's done?]

---

## 📝 Notes

[Any additional context, links, decisions]
```

---

## 🔗 Related

**Stories:** More granular user stories live in `/stories` if needed
**Docs:** Journey documentation lives in `/brand/content/posts` (Day X posts)
**Code:** Implementation lives in `/lib` (Flutter) and `/core` (Backend)

---

## 💡 Philosophy

**Use Cases = Features**
- One use case = One cohesive feature
- Independent, shippable
- Clear acceptance criteria

**Days = Journey Documentation**
- Day 1, Day 2, etc. = Personal journey posts
- Use cases are decoupled from days
- Same use case can span multiple days
- Multiple use cases can happen in one day

**KISS Over Tools**
- Markdown files > JIRA (for now)
- Simple numbering > Complex tracking
- Git history = Change tracking
- When it gets complex, then tools

---

**Last Updated:** December 29, 2025
**Next Use Case:** UC-002 (To-Do Management) - after UC-001 ships
