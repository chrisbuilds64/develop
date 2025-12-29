# UC-001: YouTube Link Manager

**Created:** December 29, 2025
**Status:** 🔄 In Progress
**Goal:** Ship a working YouTube bookmark manager TODAY
**Principle:** Concrete implementation > Abstract planning

---

## 🎯 The Problem

**Current situation:**
- I watch many YouTube videos with valuable content
- Want to save and organize them for later
- YouTube's native features (playlists, likes, "Watch Later") are insufficient
- Saving in browser bookmarks = losing control
- Need: Quick save with tags, easy retrieval by tags

**What annoys me most:**
- Can't tag videos with custom keywords (e.g., "Workout", "Triceps", "Cable")
- Can't filter by multiple tags
- No quick "share from YouTube → save to my app" workflow
- YouTube's algorithm pushes recommendations, not my saved content

---

## ✅ Today's Goal (Concrete, Achievable)

**Build a simple app where I can:**
1. Share a YouTube link from YouTube app → Tweight saves it
2. Add custom tags when saving (e.g., "Workout", "Triceps", "Cable")
3. Filter saved videos by tags
4. Click a video → Opens in YouTube app and plays

**That's it. Nothing more.**

---

## 🚫 What I'm NOT Building Today

- ❌ Abstract "Item" system for all content types
- ❌ To-Do management
- ❌ Note-taking features
- ❌ Generic metadata framework
- ❌ Perfect database normalization
- ❌ Multiple content types

**Why not?**
- YAGNI (You Ain't Gonna Need It - yet)
- Ship working app > Build flexible architecture
- Premature abstraction = Scope creep
- Today: YouTube links. Tomorrow: Maybe To-Dos (if needed)

---

## 📱 User Stories

### Story 1: Save Video from YouTube
**As a user**
I want to share a YouTube video to Tweight
So that I can save it with custom tags

**Acceptance Criteria:**
- User watches video in YouTube app
- User clicks "Share" button
- User selects "Tweight" from share menu
- Tweight opens, shows save dialog
- User can add tags (comma-separated or chip UI)
- User clicks "Save"
- Video is saved to database
- User sees confirmation

---

### Story 2: Browse Saved Videos
**As a user**
I want to see all my saved videos
So that I can review what I've saved

**Acceptance Criteria:**
- User opens Tweight app
- User sees list of saved videos
- Each video shows: Thumbnail, Title, Tags
- List is sorted by date saved (newest first)

---

### Story 3: Filter by Tags
**As a user**
I want to filter videos by tags
So that I can find specific content quickly

**Acceptance Criteria:**
- User can select one or more tags
- List updates to show only videos with those tags
- User can clear filter to see all videos
- Tag selection is intuitive (chips or dropdown)

---

### Story 4: Play Video
**As a user**
I want to open a saved video in YouTube
So that I can watch it

**Acceptance Criteria:**
- User taps on a video in the list
- Video opens in YouTube app (or web if no app)
- Video starts playing

---

## 🗄️ Database Schema (Simple)

### Table: `videos`

```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    thumbnail_url TEXT,
    tags TEXT,  -- Comma-separated for simplicity (normalize later if needed)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Why this simple?**
- No complex tag table (yet)
- No many-to-many relationships (yet)
- Comma-separated tags = good enough for V1
- Can refactor later when/if needed

**Example row:**
```json
{
    "id": 1,
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Cable Tricep Pushdown Tutorial",
    "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
    "tags": "workout,triceps,cable",
    "created_at": "2025-12-29 14:30:00"
}
```

---

## 🔌 API Endpoints

### 1. Save Video
**POST /videos**

**Request:**
```json
{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "tags": ["workout", "triceps", "cable"]
}
```

**Response:**
```json
{
    "id": 1,
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Cable Tricep Pushdown Tutorial",
    "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
    "tags": "workout,triceps,cable",
    "created_at": "2025-12-29T14:30:00Z"
}
```

**Backend logic:**
- Parse YouTube URL to extract video ID
- Fetch video metadata (title, thumbnail) from YouTube (optional for V1)
- Store in database
- Return saved video

---

### 2. Get All Videos
**GET /videos**

**Query Parameters:**
- `tags` (optional): Filter by tags (comma-separated)

**Examples:**
- `GET /videos` → All videos
- `GET /videos?tags=workout` → Videos tagged "workout"
- `GET /videos?tags=workout,triceps` → Videos with BOTH tags

**Response:**
```json
{
    "videos": [
        {
            "id": 1,
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "title": "Cable Tricep Pushdown Tutorial",
            "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg",
            "tags": "workout,triceps,cable",
            "created_at": "2025-12-29T14:30:00Z"
        }
    ]
}
```

---

### 3. Delete Video (Optional for V1)
**DELETE /videos/{id}**

**Response:**
```json
{
    "success": true,
    "message": "Video deleted"
}
```

---

## 📱 Frontend (Flutter)

### Screen 1: Video List
**Features:**
- List of saved videos
- Each item shows: Thumbnail, Title, Tags
- Pull to refresh
- Tap video → Opens in YouTube

**UI Components:**
- AppBar with filter button
- ListView.builder for videos
- VideoCard widget (thumbnail + title + tags)

---

### Screen 2: Save Video (Share Dialog)
**Triggered by:** Share from YouTube

**Features:**
- URL auto-filled from share intent
- Tag input (chips or text field)
- Save button

**Flow:**
1. User shares from YouTube
2. Tweight receives URL via share intent
3. Show dialog: "Save this video?"
4. User adds tags
5. User clicks Save
6. POST to backend
7. Show confirmation
8. Close dialog (or navigate to list)

---

### Screen 3: Filter by Tags (Optional Modal/Dialog)
**Features:**
- Show all unique tags from saved videos
- User can select tags
- Apply filter
- Clear filter

---

## 🛠️ Implementation Steps (Order Matters)

### Phase 1: Backend Foundation
1. ✅ Create `videos` table (SQLite)
2. ✅ Create Video model (SQLAlchemy)
3. ✅ POST /videos endpoint (save video)
4. ✅ GET /videos endpoint (list videos, with tag filter)
5. ✅ Test with curl/Postman

### Phase 2: Frontend Foundation
6. ✅ Create VideoList screen (empty state first)
7. ✅ Fetch videos from API and display
8. ✅ Create VideoCard widget (thumbnail, title, tags)

### Phase 3: Share Integration
9. ✅ Configure share intent receiver (iOS/Android)
10. ✅ Create SaveVideo dialog/screen
11. ✅ POST video to backend when saved
12. ✅ Navigate to list after save

### Phase 4: Tag Filtering
13. ✅ Add tag filter UI
14. ✅ Filter videos by selected tags
15. ✅ Clear filter option

### Phase 5: Polish
16. ✅ Open video in YouTube when tapped
17. ✅ Pull to refresh
18. ✅ Error handling
19. ✅ Loading states

---

## 🎯 Success Criteria (Today)

**Done = I can:**
1. ✅ Share YouTube link from YouTube app to Tweight
2. ✅ Add tags when saving
3. ✅ See list of all saved videos
4. ✅ Filter by tag (e.g., "workout")
5. ✅ Tap video → Opens in YouTube and plays

**Nice-to-have (if time):**
- Thumbnail display
- Pull to refresh
- Delete video

---

## 🚀 Why This Approach Works

### Principles Applied:
1. **KISS (Keep It Simple)** → Simple table, simple tags
2. **YAGNI (You Ain't Gonna Need It)** → No abstract Item system yet
3. **Lean/Agile** → Ship working feature, iterate later
4. **Use Case Driven** → Solve real problem (my YouTube mess)
5. **Building in Public** → Real feature, real user (me)

### What I Can Do LATER (If Needed):
- Normalize tags (separate table, many-to-many)
- Add To-Do features
- Refactor to generic Item system
- Add notes, bookmarks, etc.

**But not today.**

---

## 📝 Content Opportunities

### Substack Post (Tonight):
**Title:** "Day 4: I Built a YouTube Bookmark Manager (and Resisted Over-Engineering)"

**Key Points:**
- Real problem solved (YouTube chaos)
- Concrete > Abstract (today)
- YAGNI in action
- Shipped working app in one day
- Vision saved for later (documented, not forgotten)

### Future Posts:
- "From Concrete to Abstract: When to Refactor"
- "Wishful Thinking vs. Walkthrough" (when I have 2+ features)
- "The Generic Item System" (when I actually need it)

---

## 🎬 Instagram Reel Idea (Later Tonight)

**Concept:** "I built this in one afternoon with AI"

**Script:**
- 0-3s: "YouTube bookmarks are a mess"
- 3-6s: "So I built my own app"
- 6-9s: Show sharing from YouTube → Tweight
- 9-12s: Show filtering by tags
- 12-15s: "Built in one afternoon with Claude Code. Building in public from Bali."

**Hook:** Relatable problem, quick solution, AI-powered, Bali lifestyle

---

**Status:** Ready to implement
**Next Step:** Create detailed prompt for Claude Code
**Expected Completion:** Tonight (Dec 29, 2025)

---

*Building in public. Solving real problems. Shipping today.* 🚀
