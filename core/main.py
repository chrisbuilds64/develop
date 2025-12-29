"""
Tweight Core API - Simple, focused, functional.

Endpoints:
- /health: Service health check
- /timer: Current server timestamp
- /videos: YouTube link management (UC-001)
"""
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

# Import database and models
from database import get_db, init_db
from models import Video
from schemas import VideoCreate, VideoResponse, VideosListResponse

app = FastAPI(title="Tweight Core API", version="0.2.0")


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    """Create database tables on startup."""
    init_db()
    print("✅ Database initialized")


@app.get("/health")
def health_check():
    """Health check endpoint - always returns OK if service is running."""
    return {"status": "ok", "service": "tweight-core", "version": "0.2.0"}


@app.get("/timer")
def get_timer():
    """Returns current server timestamp."""
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "unix": int(datetime.utcnow().timestamp())
    }


# ==================== VIDEO ENDPOINTS (UC-001) ====================

@app.post("/videos", response_model=VideoResponse, status_code=201)
def create_video(video_data: VideoCreate, db: Session = Depends(get_db)):
    """
    Save a YouTube video with tags.

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

    # Create video object
    video = Video(
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
def list_videos(tags: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Get all videos, optionally filtered by tags.

    **Query Parameters:**
    - `tags` (optional): Comma-separated tags to filter by (e.g., "workout,triceps")

    **Examples:**
    - GET /videos → All videos
    - GET /videos?tags=workout → Videos tagged "workout"
    - GET /videos?tags=workout,triceps → Videos with "workout" OR "triceps"

    **Response:**
    ```json
    {
        "videos": [...],
        "count": 10
    }
    ```
    """
    query = db.query(Video)

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
def delete_video(video_id: int, db: Session = Depends(get_db)):
    """
    Delete a video by ID.

    **Response:** 204 No Content on success
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

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
