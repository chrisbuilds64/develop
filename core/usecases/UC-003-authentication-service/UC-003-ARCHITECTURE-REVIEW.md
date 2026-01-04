# UC-003: Authentication Service - Architecture Review

**Date:** January 3, 2026
**Purpose:** Align Clerk integration with Core architecture before implementation
**Status:** Planning / Architecture Review

---

## 🎯 GOAL

Add user authentication to enable:
- Multiple users (not just Chris)
- User-specific data (videos, notes, workouts)
- Prepare for beta testers
- Foundation for future multi-user features

---

## 📊 CURRENT STATE

### **Core v0.2.0 (as of Day 10):**

```
develop/core/
├── main.py              # FastAPI app, /videos endpoints
├── models.py            # Video model (NO user_id yet)
├── database.py          # SQLite + SQLAlchemy
├── schemas.py           # Pydantic schemas
├── requirements.txt     # Dependencies
└── usecases/
    └── UC-001-youtube-link-manager.md
```

**Endpoints:**
- `GET /health` - Health check
- `GET /timer` - Server timestamp
- `POST /videos` - Create video
- `GET /videos?tags=X` - List videos (all users!)
- `DELETE /videos/{id}` - Delete video

**Current Issues:**
1. ❌ No authentication - API is wide open
2. ❌ No user concept - all videos shared globally
3. ❌ No authorization - anyone can delete anyone's videos
4. ❌ Production ready for 1 user, not for 2+

---

## 🏗️ PROPOSED ARCHITECTURE

### **Decision: Clerk**

**Why Clerk?**
- Free tier: 10,000 monthly active users
- JWT-based (portable, standard)
- SDKs for Python (FastAPI) + Flutter
- Social logins (Google, Apple, GitHub) built-in
- 1-2 hours to integrate vs. weeks to build

**What we WON'T build:**
- ❌ Password hashing
- ❌ Session management
- ❌ Email verification
- ❌ "Forgot password" flows
- ❌ Admin dashboard
- ❌ OAuth providers

**What we WILL build:**
- ✅ Thin facade in Core (`core/auth/`)
- ✅ JWT verification middleware
- ✅ User model in database
- ✅ user_id foreign keys
- ✅ Protected endpoints

---

## 📐 NEW STRUCTURE

```
develop/core/
├── main.py              # FastAPI app (UPDATED: protected endpoints)
├── models.py            # Video, User models (UPDATED: add user_id)
├── database.py          # SQLite + SQLAlchemy (unchanged)
├── schemas.py           # Pydantic schemas (UPDATED: user fields)
├── requirements.txt     # UPDATED: add clerk-backend-api
│
├── auth/                # NEW: Authentication layer
│   ├── __init__.py
│   ├── clerk.py         # Clerk integration (verify JWT)
│   ├── middleware.py    # FastAPI dependency (get_current_user)
│   └── schemas.py       # Auth-related schemas
│
└── usecases/
    ├── UC-001-youtube-link-manager.md
    └── UC-003-authentication-service.md  # NEW
```

---

## 🔄 MIGRATION PLAN

### **Phase 1: Core Changes (30-60 min)**

#### **1. Add User Model**

```python
# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

class User(Base):
    """
    User model - synced from Clerk.

    We don't store passwords (Clerk handles that).
    We only store: Clerk user_id, email, display name.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String, unique=True, nullable=False, index=True)  # From Clerk JWT
    email = Column(String, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    videos = relationship("Video", back_populates="user")


class Video(Base):
    """Updated: Add user_id foreign key"""
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # NEW!
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="videos")
```

**Migration:** Need Alembic migration to add `user_id` column to existing videos table.

---

#### **2. Add Clerk Integration**

```python
# auth/clerk.py
from clerk_backend_api import Clerk
from clerk_backend_api.jwks_helpers import authenticate_request
from fastapi import HTTPException, Request
from typing import Optional
import os

clerk_client = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

def verify_clerk_token(token: str) -> dict:
    """
    Verify Clerk JWT token.

    Returns decoded token with user info:
    {
        "sub": "user_2abc123...",  # Clerk user ID
        "email": "chris@example.com",
        "name": "Chris"
    }

    Raises HTTPException if invalid.
    """
    try:
        # Clerk's JWT verification
        payload = authenticate_request(
            request=None,
            token=token,
            secret_key=os.getenv("CLERK_SECRET_KEY"),
            # ... Clerk config
        )
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


def get_or_create_user(db: Session, clerk_id: str, email: str, name: str) -> User:
    """
    Get existing user or create new one from Clerk data.

    Called on first API request after Clerk login.
    """
    user = db.query(User).filter(User.clerk_id == clerk_id).first()

    if not user:
        # First time user - create in our DB
        user = User(clerk_id=clerk_id, email=email, name=name)
        db.add(user)
        db.commit()
        db.refresh(user)

    return user
```

---

#### **3. Add FastAPI Dependency**

```python
# auth/middleware.py
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from auth.clerk import verify_clerk_token, get_or_create_user
from models import User

def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency: Extract and verify user from JWT.

    Usage in endpoints:

    @app.get("/videos")
    def list_videos(user: User = Depends(get_current_user)):
        # user is authenticated User object
        videos = db.query(Video).filter(Video.user_id == user.id).all()
        ...

    Raises 401 if:
    - No Authorization header
    - Invalid token
    - Clerk user not found
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.replace("Bearer ", "")

    # Verify with Clerk
    payload = verify_clerk_token(token)

    clerk_id = payload.get("sub")
    email = payload.get("email")
    name = payload.get("name", "")

    if not clerk_id or not email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Get or create user in our DB
    user = get_or_create_user(db, clerk_id, email, name)

    return user
```

---

#### **4. Update Endpoints**

```python
# main.py (UPDATED)
from auth.middleware import get_current_user
from models import User

@app.post("/videos", response_model=VideoResponse, status_code=201)
def create_video(
    video_data: VideoCreate,
    user: User = Depends(get_current_user),  # NEW: Require auth
    db: Session = Depends(get_db)
):
    """
    Save a YouTube video (user-specific).

    Requires: Authorization: Bearer <clerk-jwt>
    """
    # ... video creation logic ...

    video = Video(
        user_id=user.id,  # NEW: Associate with user
        url=video_data.url,
        title=None,
        thumbnail_url=thumbnail_url,
        tags=tags_str
    )

    db.add(video)
    db.commit()
    db.refresh(video)

    return video


@app.get("/videos", response_model=VideosListResponse)
def list_videos(
    tags: Optional[str] = None,
    user: User = Depends(get_current_user),  # NEW: Require auth
    db: Session = Depends(get_db)
):
    """
    Get user's videos (filtered by user_id).
    """
    query = db.query(Video).filter(Video.user_id == user.id)  # NEW: Filter by user

    # ... rest of logic ...

    videos = query.order_by(Video.created_at.desc()).all()
    return VideosListResponse(videos=videos, count=len(videos))


@app.delete("/videos/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    user: User = Depends(get_current_user),  # NEW: Require auth
    db: Session = Depends(get_db)
):
    """
    Delete user's video (authorization check).
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == user.id  # NEW: Ensure user owns this video
    ).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found or not authorized")

    db.delete(video)
    db.commit()
    return None
```

---

### **Phase 2: Flutter Changes (30-60 min)**

```dart
// lib/services/auth_service.dart (NEW)
import 'package:clerk_flutter/clerk_flutter.dart';

class AuthService {
  final Clerk clerk;

  AuthService() : clerk = Clerk(publishableKey: Environment.clerkPublishableKey);

  Future<String?> getToken() async {
    // Get Clerk JWT token
    final session = await clerk.session.getToken();
    return session?.jwt;
  }

  Future<void> signIn() async {
    // Clerk handles sign-in flow (Google, Apple, etc.)
    await clerk.signIn();
  }

  Future<void> signOut() async {
    await clerk.signOut();
  }
}


// lib/services/api_service.dart (UPDATED)
class ApiService {
  final AuthService _authService;

  Future<List<Video>> getVideos({List<String>? tags}) async {
    final token = await _authService.getToken();

    if (token == null) {
      throw Exception("Not authenticated");
    }

    final response = await http.get(
      Uri.parse('$baseUrl/videos'),
      headers: {
        'Authorization': 'Bearer $token',  // NEW: Add JWT
      },
    );

    // ... rest of logic ...
  }
}
```

---

## 🔐 SECURITY CONSIDERATIONS

### **What Clerk Handles:**
- ✅ Password storage (hashing, salting)
- ✅ Session management
- ✅ OAuth providers (Google, Apple, GitHub)
- ✅ Email verification
- ✅ Password reset
- ✅ JWT generation & signing

### **What We Handle:**
- ✅ JWT verification (Clerk SDK)
- ✅ User-to-data association (user_id foreign keys)
- ✅ Authorization (user can only access their own videos)
- ✅ Rate limiting (future)

### **Environment Variables:**
```bash
# .env (Backend)
CLERK_SECRET_KEY=sk_test_...

# Flutter (environment.dart)
CLERK_PUBLISHABLE_KEY=pk_test_...
```

**NEVER commit these to Git!**

---

## 📋 DATABASE MIGRATION

### **Alembic Migration (Required):**

```bash
# Generate migration
alembic revision --autogenerate -m "add user model and user_id to videos"

# Review migration file
# - Adds users table
# - Adds user_id column to videos (nullable=True initially)
# - Creates foreign key constraint

# Apply to localhost
alembic upgrade head

# Test locally
# Then apply to staging
# Then apply to production
```

**Migration Challenge:**
- Existing videos have no user_id
- Options:
  1. Delete all existing videos (acceptable for Day 10, only Chris's data)
  2. Assign all to default user (Chris)
  3. Make user_id nullable (temporary, not recommended)

**Decision:** Option 1 (delete existing, fresh start with auth)

---

## ⚠️ BREAKING CHANGES

### **API Changes:**

**Before (UC-001, no auth):**
```bash
# Anyone can access
curl https://api.chrisbuilds64.com/videos

# Anyone can create
curl -X POST https://api.chrisbuilds64.com/videos \
  -H "Content-Type: application/json" \
  -d '{"url": "...", "tags": ["workout"]}'
```

**After (UC-003, with auth):**
```bash
# Requires JWT
curl https://api.chrisbuilds64.com/videos \
  -H "Authorization: Bearer eyJhbGc..."

# 401 Unauthorized without token
```

### **Flutter App Changes:**
- User must sign in before using app
- Sign-in flow (Clerk UI)
- Token management
- Logout functionality

---

## 🎯 IMPLEMENTATION STEPS

### **Today (Jan 3 - 2-3 hours):**

**Backend (Core):**
1. ✅ Create `auth/` directory structure
2. ✅ Add User model to `models.py`
3. ✅ Create `auth/clerk.py` (JWT verification)
4. ✅ Create `auth/middleware.py` (get_current_user dependency)
5. ✅ Update `requirements.txt` (add clerk-backend-api)
6. ✅ Update all `/videos` endpoints (add auth dependency)
7. ✅ Test locally with mock JWT

**Migration:**
8. ✅ Create Alembic migration
9. ✅ Apply to local DB
10. ✅ Verify schema

**Documentation:**
11. ✅ Create UC-003-authentication-service.md
12. ✅ Update ARCHITECTURE.md

### **Tomorrow (Jan 4):**

**Clerk Setup:**
1. Create Clerk account
2. Get API keys
3. Configure OAuth providers (Google, Apple)

**Backend Testing:**
4. Deploy to staging
5. Test with real Clerk JWT
6. Verify user creation

**Flutter:**
7. Add clerk_flutter package
8. Implement sign-in flow
9. Update API calls with JWT
10. Test end-to-end

**Deploy:**
11. Deploy to production
12. Test with multiple users
13. Day 11 post about authentication journey

---

## 📊 SUCCESS CRITERIA

After UC-003 implementation:

✅ **Backend:**
- User can sign in via Clerk (Google/Apple)
- API requires valid JWT
- Videos are user-specific
- User can only delete their own videos

✅ **Flutter:**
- Sign-in flow works
- Token automatically included in API calls
- User can sign out

✅ **Security:**
- No passwords stored in our DB
- JWT verification works
- Unauthorized requests return 401

✅ **Ready for Beta:**
- Lily can create account
- Lars can create account
- Their videos are separate
- No data leakage between users

---

## 💡 KISS PRINCIPLES

**What we're NOT doing:**
- ❌ Building custom auth (use Clerk)
- ❌ Role-based access control (YAGNI - not needed yet)
- ❌ Complex permission systems (YAGNI)
- ❌ Audit logs (YAGNI)
- ❌ Multi-factor authentication (Clerk free tier doesn't have it, fine for now)

**What we ARE doing:**
- ✅ Thin facade over Clerk
- ✅ User-specific data (simple foreign key)
- ✅ JWT verification (standard, portable)
- ✅ Foundation for growth (can add features later)

**Scope:**
- Building for: 10 users (Lily, Lars, Chris, + 7 beta testers)
- Not building for: 1 million users
- Infrastructure enables growth, doesn't anticipate it

---

## 🚀 READY TO START?

**Estimated Time:**
- Backend changes: 1.5-2 hours
- Migration: 15 min
- Documentation: 30 min
- **Total: 2-3 hours today**

**Dependencies:**
- ✅ Core v0.2.0 (current state)
- ✅ Clerk account (free tier)
- ✅ Python environment
- ✅ Alembic (for migrations)

**Next Step:** Create `auth/` directory and start with User model

---

**Questions for Chris before we start:**

1. ✅ Delete existing videos in DB? (Fresh start with auth)
2. ✅ Start with backend changes today, Flutter tomorrow?
3. ✅ Test locally first, deploy to staging before production?

Let's build! 🚀
