# UC-001 Implementation Guide - YouTube Link Manager

**Context:** Read [UC-001-youtube-link-manager.md](UC-001-youtube-link-manager.md) first for full context.

---

## 🎯 Goal

Build a simple YouTube link manager for Tweight app TODAY.

**User flow:**
1. User shares YouTube link from YouTube app → Tweight receives it
2. User adds tags (e.g., "workout, triceps, cable")
3. Video is saved to database
4. User can see list of all saved videos
5. User can filter by tags
6. User can tap video → Opens in YouTube app

---

## 📋 Requirements

### Backend (FastAPI)

**1. Database Schema (SQLite)**
Create table `videos`:
- id (INTEGER, PRIMARY KEY, AUTOINCREMENT)
- url (TEXT, NOT NULL)
- title (TEXT, nullable - can extract later from YouTube)
- thumbnail_url (TEXT, nullable)
- tags (TEXT - comma-separated for simplicity)
- created_at (TIMESTAMP, default current time)

**2. API Endpoints**

**POST /videos**
- Accept: `{"url": "...", "tags": ["tag1", "tag2"]}`
- Parse YouTube URL, extract video ID
- Optionally: Fetch title/thumbnail from YouTube (nice-to-have, not critical)
- Store in database (tags as comma-separated string)
- Return saved video as JSON

**GET /videos**
- Query param: `tags` (optional, comma-separated)
- If no tags: Return all videos
- If tags provided: Filter videos that contain ANY of those tags
- Return as JSON array

**DELETE /videos/{id}** (optional, low priority)
- Delete video by ID

### Frontend (Flutter)

**3. Share Intent Receiver**
- Configure iOS/Android to receive YouTube URLs via share
- When app receives shared URL, navigate to SaveVideo screen

**4. SaveVideo Screen/Dialog**
- Show URL (pre-filled from share)
- Tag input field (text field or chips)
- Save button
- On save: POST to backend, show success, navigate to list

**5. VideoList Screen**
- Fetch videos from GET /videos
- Display as list: Thumbnail (if available), Title (or URL if no title), Tags
- Pull to refresh
- Tap video → Open in YouTube app (use url_launcher)

**6. Tag Filter (Simple)**
- Filter button in AppBar
- Show dialog with tag input
- Filter videos by tag(s)
- Clear filter option

---

## 🛠️ Implementation Approach

### Principles:
- **KISS:** Simple, straightforward, no over-engineering
- **Working > Perfect:** Get it working first, polish later
- **Real data:** Use real YouTube URLs for testing

### Tech Stack:
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Frontend:** Flutter + http package + url_launcher

### Don't Do (Yet):
- ❌ Complex tag normalization (separate table)
- ❌ User authentication
- ❌ Video metadata caching
- ❌ Offline support
- ❌ Advanced search
- ❌ Multiple content types

---

## 📝 Step-by-Step Implementation Order

### Phase 1: Backend (30-45 min)

**Step 1: Database Model**
- Create `models.py` (or extend existing)
- Define Video model (SQLAlchemy)
- Create table via `Base.metadata.create_all()`

**Step 2: API Endpoints**
- Create `/videos POST` endpoint
  - Accept JSON: `{"url": "...", "tags": ["..."]}`
  - Basic YouTube URL validation (contains youtube.com or youtu.be)
  - Extract video ID from URL
  - Store with tags as comma-separated string
  - Return saved video

- Create `/videos GET` endpoint
  - Accept query param: `tags` (optional)
  - If tags: Filter with SQL LIKE (simple)
  - Return videos as JSON array

**Step 3: Test Backend**
- Use curl or Postman
- POST a video with tags
- GET all videos
- GET videos filtered by tag
- Verify database content

---

### Phase 2: Frontend Foundation (30-45 min)

**Step 4: Video Model (Dart)**
- Create `models/video.dart`
- Define Video class with fromJson/toJson

**Step 5: API Service**
- Create `services/video_service.dart`
- Methods: `saveVideo()`, `getVideos()`, `getVideosByTags()`
- Use http package to call backend

**Step 6: VideoList Screen**
- Create `screens/video_list_screen.dart`
- Fetch videos on init
- Display as ListView
- Simple VideoCard widget (for now just show title/URL + tags)
- Pull to refresh

**Step 7: Test Integration**
- Run backend (localhost:8000)
- Run Flutter app
- Manually add video via Postman
- Verify it shows in Flutter app

---

### Phase 3: Share Integration (30-45 min)

**Step 8: Share Intent Configuration**
- Android: Update `AndroidManifest.xml` for share intent
- iOS: Update `Info.plist` for share extension
- Both: Accept text/plain and text/url

**Step 9: SaveVideo Screen**
- Create `screens/save_video_screen.dart`
- Receive shared URL via intent
- Tag input (TextFormField, split by comma)
- Save button → POST to backend
- Show success message
- Navigate to VideoList

**Step 10: Main App Navigation**
- Update `main.dart` to handle share intent
- Route to SaveVideo screen when URL received
- Otherwise show VideoList screen

**Step 11: Test Share Flow**
- Share YouTube link from YouTube app
- Tweight should open with SaveVideo screen
- Add tags, save
- Verify video appears in list

---

### Phase 4: Tag Filtering (20-30 min)

**Step 12: Filter UI**
- Add filter icon button in VideoList AppBar
- Show dialog with tag input
- Apply filter: Call `getVideosByTags(tags)`
- Clear filter option

**Step 13: Tag Chips Display**
- Show all unique tags (extract from videos)
- User can tap to filter by that tag

---

### Phase 5: Polish (20-30 min)

**Step 14: Open in YouTube**
- Add url_launcher dependency
- On video tap: `launchUrl(videoUrl)`
- Opens in YouTube app (or browser)

**Step 15: Thumbnail (Nice-to-Have)**
- If backend fetched thumbnail: Display with Image.network()
- If not: Placeholder or just title

**Step 16: Error Handling**
- Loading states
- Empty state ("No videos yet")
- Network error handling
- Invalid URL handling

---

## 🧪 Testing Checklist

**Backend:**
- [ ] Can save video via POST /videos
- [ ] Can get all videos via GET /videos
- [ ] Can filter by tag via GET /videos?tags=workout
- [ ] Tags are stored correctly (comma-separated)
- [ ] Database persists data

**Frontend:**
- [ ] Video list displays saved videos
- [ ] Pull to refresh works
- [ ] Tapping video opens YouTube
- [ ] Share from YouTube opens Tweight
- [ ] Can save video with tags
- [ ] Tag filtering works
- [ ] Error states display correctly

**End-to-End:**
- [ ] Share YouTube link → Save with tags → See in list → Filter by tag → Open video
- [ ] Works on iOS and/or Android (at least macOS for testing)

---

## 💡 Implementation Tips

### YouTube URL Parsing
```python
# Simple approach (backend)
def extract_video_id(url: str) -> str:
    if "youtube.com/watch?v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return None
```

### Thumbnail URL (if needed)
```python
# YouTube thumbnail URL format
thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
```

### Tag Filtering (SQL)
```sql
-- Simple LIKE query (good enough for V1)
SELECT * FROM videos WHERE tags LIKE '%workout%'
```

### Share Intent (Flutter)
- Use `receive_sharing_intent` package or `uni_links` package
- Or handle manually with platform channels (more work)

---

## 🚀 Success Criteria

**Done when:**
1. ✅ I can share a YouTube link from YouTube app to Tweight
2. ✅ I can add tags when saving
3. ✅ I can see list of saved videos
4. ✅ I can filter by tag
5. ✅ I can tap video and it opens in YouTube

**Bonus (if time):**
- Thumbnails display
- Delete video option
- Tag suggestions (from existing tags)

---

## 📦 Deliverables

**Code:**
- Backend: Updated `main.py`, new `models.py` (or extended)
- Frontend: New screens, services, models
- Database: SQLite file with videos table

**Documentation:**
- This file (implementation notes)
- Updated README with setup instructions

**Git Commit:**
- Meaningful commit message
- All files added and pushed

**Substack Post:**
- Write about today's implementation
- Show screenshots
- Explain choices (concrete > abstract)

---

## 🎯 Final Notes

**Keep it simple:**
- Don't fetch YouTube metadata if it's complicated (just store URL, add title later)
- Don't normalize tags yet (comma-separated is fine)
- Don't build perfect UI (functional > beautiful for V1)

**Focus on flow:**
- Share → Save → List → Filter → Open
- That's the core. Everything else is polish.

**Time-boxing:**
- Backend: 45 min max
- Frontend foundation: 45 min max
- Share integration: 45 min max
- Tag filtering: 30 min max
- Polish: 30 min max
- **Total: 3-4 hours max**

**If stuck:**
- Ship minimal version
- Document what's missing
- Iterate tomorrow

---

**Let's build!** 🚀

**Status:** Ready for implementation
**Next:** Start with Backend Phase 1
**Timeline:** Complete by tonight (Dec 29, 2025)
