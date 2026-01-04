# UC-001: YouTube Link Manager - Future Improvements

**Status:** Backlog (for later iterations)

---

## 📋 Planned Improvements

### 1. Native iOS Share Extension
**Current:** Clipboard workaround (copy link → open app → auto-paste)
**Future:** Direct share from YouTube app
- Create proper iOS Share Extension target in Xcode
- Register for URL/text sharing
- Appears in iOS share sheet
- Pre-fills URL in save dialog

**Priority:** Medium
**Effort:** ~2-3 hours (requires Xcode work)

---

### 2. Tag Suggestions from History
**Current:** Free text input, no suggestions
**Future:** Smart tag autocomplete
- Backend stores unique tags across all videos
- New endpoint: `GET /tags` returns all used tags
- Frontend shows tag suggestions as user types
- Quick-add popular tags with chips/pills

**Priority:** High (improves UX significantly)
**Effort:** ~1 hour
**Technical:**
- Backend: New `Tag` model or aggregate query on `Video.tags`
- Frontend: Autocomplete widget or tag chip selector

---

### 3. View Mode Switcher
**Current:** Card list view only
**Future:** Multiple view modes
- **Compact List:** Title + tags only (more videos per screen)
- **Card View:** Current (thumbnail + title + tags + date)
- **Grid View:** Pure thumbnails (like YouTube's grid)

**Priority:** Medium
**Effort:** ~2 hours
**Technical:**
- Add view mode toggle in AppBar
- Store preference locally (SharedPreferences)
- Create separate widgets for each view mode

---

### 4. Multi-Tenancy / User Management
**Status:** To be specified tomorrow
**Reminder:** Create detailed use case document
**Context:** Support multiple users accessing same backend
**Questions to answer:**
- Authentication mechanism (JWT, sessions, OAuth)?
- User registration flow?
- Data isolation (user_id foreign key)?
- Shared vs. private videos?

**Priority:** TBD
**Effort:** TBD

---

## 🎯 Implementation Strategy

**Principle:** Ship working features incrementally
- Each improvement should be completable in 1-3 hours
- Test on iPhone before moving to next feature
- Commit after each working feature
- Build in public (document in Substack posts)

---

## 📝 Notes

Created: December 29, 2025
Context: After shipping UC-001 MVP with clipboard workaround
Philosophy: KISS → Ship → Learn → Iterate
