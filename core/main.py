"""
Tweight Core API - Simple, focused, functional.

Endpoints:
- /health: Service health check
- /timer: Current server timestamp
- /videos: YouTube link management (UC-001, now with auth - UC-003)

UC-003: Authentication with Clerk (or Mock for local dev)
- All /videos endpoints now require authentication
- User-specific data (videos belong to users)
- Bearer token required in Authorization header
"""
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import database and models
from database import get_db, init_db
from models import Video, User
from schemas import VideoCreate, VideoResponse, VideosListResponse

# UC-003: Import authentication
from auth.middleware import get_current_user
from auth.login_handler import ClerkLoginHandler
from pydantic import BaseModel

app = FastAPI(title="Tweight Core API", version="0.3.0")  # UC-003: Version bump

# Login request/response schemas
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Create database tables on startup."""
    init_db()
    print("✅ Database initialized")


@app.get("/health")
def health_check():
    """Health check endpoint - always returns OK if service is running."""
    return {"status": "ok", "service": "tweight-core", "version": "0.3.0"}


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login endpoint - authenticates user and returns JWT token.

    Works in two modes:
    - Development (ENV=development): Accepts mock credentials
    - Production (ENV=production): Uses Clerk authentication
    """
    login_handler = ClerkLoginHandler()
    try:
        result = await login_handler.sign_in(request.email, request.password)
        return LoginResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/timer")
def get_timer():
    """Returns current server timestamp."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "unix": int(datetime.utcnow().timestamp())
    }


# ==================== VIDEO ENDPOINTS (UC-001) ====================

@app.post("/videos", response_model=VideoResponse, status_code=201)
def create_video(
    video_data: VideoCreate,
    user: User = Depends(get_current_user),  # UC-003: Require authentication
    db: Session = Depends(get_db)
):
    """
    Save a YouTube video with tags (user-specific).

    **UC-003: Authentication Required**
    - Requires: Authorization: Bearer <token>
    - Video will be associated with authenticated user

    **Request:**
    ```json
    {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "tags": ["workout", "triceps", "cable"]
    }
    ```

    **Response:**
    Returns the created video with ID and metadata.
    """
    # Extract video ID from URL (simple approach)
    video_id = extract_video_id(video_data.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    # Generate thumbnail URL
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"

    # Convert tags list to comma-separated string
    tags_str = ",".join(video_data.tags) if video_data.tags else ""

    # Create video object (UC-003: Associate with user)
    video = Video(
        user_id=user.id,  # UC-003: Added
        url=video_data.url,
        title=None,  # Can fetch from YouTube API later
        thumbnail_url=thumbnail_url,
        tags=tags_str
    )

    # Save to database
    db.add(video)
    db.commit()
    db.refresh(video)

    return video


@app.get("/videos", response_model=VideosListResponse)
def list_videos(
    tags: Optional[str] = None,
    user: User = Depends(get_current_user),  # UC-003: Require authentication
    db: Session = Depends(get_db)
):
    """
    Get user's videos, optionally filtered by tags.

    **UC-003: Authentication Required**
    - Requires: Authorization: Bearer <token>
    - Returns only videos belonging to authenticated user

    **Query Parameters:**
    - `tags` (optional): Comma-separated tags to filter by (e.g., "workout,triceps")

    **Examples:**
    - GET /videos → All user's videos
    - GET /videos?tags=workout → User's videos tagged "workout"
    - GET /videos?tags=workout,triceps → User's videos with "workout" OR "triceps"

    **Response:**
    ```json
    {
        "videos": [...],
        "count": 10
    }
    ```
    """
    # UC-003: Filter by user_id (only user's own videos)
    query = db.query(Video).filter(Video.user_id == user.id)

    # Filter by tags if provided
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        # Simple LIKE query - finds if any tag is in the tags string
        filters = [Video.tags.like(f"%{tag}%") for tag in tag_list]
        # OR condition: video matches if it has ANY of the tags
        from sqlalchemy import or_
        query = query.filter(or_(*filters))

    # Order by newest first
    videos = query.order_by(Video.created_at.desc()).all()

    return VideosListResponse(videos=videos, count=len(videos))


@app.delete("/videos/{video_id}", status_code=204)
def delete_video(
    video_id: int,
    user: User = Depends(get_current_user),  # UC-003: Require authentication
    db: Session = Depends(get_db)
):
    """
    Delete a video by ID (authorization check).

    **UC-003: Authentication Required**
    - Requires: Authorization: Bearer <token>
    - User can only delete their own videos

    **Response:**
    - 204 No Content on success
    - 404 Not Found if video doesn't exist or belongs to another user
    """
    # UC-003: Ensure video exists AND belongs to user
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == user.id  # Authorization check
    ).first()

    if not video:
        raise HTTPException(
            status_code=404,
            detail="Video not found or not authorized to delete"
        )

    db.delete(video)
    db.commit()
    return None


# ==================== HELPER FUNCTIONS ====================

def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.

    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    """
    if "youtube.com/watch?v=" in url:
        # Extract from query parameter
        parts = url.split("v=")
        if len(parts) > 1:
            video_id = parts[1].split("&")[0]  # Remove other params
            return video_id
    elif "youtu.be/" in url:
        # Extract from short URL
        parts = url.split("youtu.be/")
        if len(parts) > 1:
            video_id = parts[1].split("?")[0]  # Remove query params
            return video_id
    elif "youtube.com/shorts/" in url:
        # Extract from YouTube Shorts URL
        parts = url.split("youtube.com/shorts/")
        if len(parts) > 1:
            video_id = parts[1].split("?")[0]  # Remove query params
            return video_id
    return None
