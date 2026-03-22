"""
AccoSite Builder - API Routes

Project CRUD, section save, AI text generation, image upload, website export.
"""
import os
import io
import zipfile
import uuid
from typing import Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel, Field

from api.dependencies import get_current_user
from adapters.auth import UserInfo
from modules.accosite.repository import ProjectRepository
from modules.accosite.service import AccoSiteService
from modules.accosite.generator import generate_website
from modules.accosite.models import AMENITY_CATALOGUE
from adapters.ai.base import AIAdapter
from infrastructure.config import config

router = APIRouter(prefix="/accosite", tags=["accosite"])


# ─── Dependencies ────────────────────────────────────────────────────────────

DATA_DIR = os.getenv("ACCOSITE_DATA_DIR", os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data", "accosite"
))


def get_project_repo() -> ProjectRepository:
    return ProjectRepository(DATA_DIR)


def get_accosite_service() -> AccoSiteService:
    if config.ENV in ("test",):
        from adapters.ai.mock import MockAIAdapter
        return AccoSiteService(MockAIAdapter())
    from adapters.ai.anthropic_adapter import AnthropicAdapter
    return AccoSiteService(AnthropicAdapter())


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class SaveSectionRequest(BaseModel):
    data: Any  # dict for single sections, list for arrays (rooms, reviews, faq)


class UpdateStepRequest(BaseModel):
    step: int = Field(..., ge=1, le=10)
    completed: bool = True


class GenerateTextRequest(BaseModel):
    field: str  # about, history, policies, room_short, room_long, location, getting_here, faq, footer, privacy, seo
    category_id: Optional[str] = None


# ─── Project CRUD ────────────────────────────────────────────────────────────

@router.get("/projects")
async def list_projects(
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    return repo.list_projects(current_user.user_id)


@router.post("/projects", status_code=201)
async def create_project(
    body: CreateProjectRequest,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = repo.create(current_user.user_id, body.name)
    return {
        "id": project.id,
        "slug": project.slug,
        "name": project.property_info.name,
    }


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = repo.get(current_user.user_id, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    from dataclasses import asdict
    return asdict(project)


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    if not repo.delete(current_user.user_id, project_id):
        raise HTTPException(404, "Project not found")


# ─── Section Save ────────────────────────────────────────────────────────────

@router.put("/projects/{project_id}/section/{section}")
async def save_section(
    project_id: str,
    section: str,
    body: SaveSectionRequest,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    if not repo.save_section(current_user.user_id, project_id, section, body.data):
        raise HTTPException(404, "Project not found")
    return {"ok": True}


@router.put("/projects/{project_id}/step")
async def update_step(
    project_id: str,
    body: UpdateStepRequest,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    if not repo.update_step(current_user.user_id, project_id, body.step, body.completed):
        raise HTTPException(404, "Project not found")
    return {"ok": True}


# ─── AI Text Generation ─────────────────────────────────────────────────────

@router.post("/projects/{project_id}/generate")
async def generate_text(
    project_id: str,
    body: GenerateTextRequest,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
    service: AccoSiteService = Depends(get_accosite_service),
):
    project = repo.get(current_user.user_id, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    generators = {
        "about": lambda: service.generate_about(project),
        "history": lambda: service.generate_history(project),
        "policies": lambda: service.generate_policies(project),
        "room_short": lambda: service.generate_room_description(project, body.category_id, "short"),
        "room_long": lambda: service.generate_room_description(project, body.category_id, "long"),
        "location": lambda: service.generate_location_about(project),
        "getting_here": lambda: service.generate_getting_here(project),
        "faq": lambda: service.generate_faq(project),
        "footer": lambda: service.generate_footer(project),
        "privacy": lambda: service.generate_privacy_policy(project),
        "seo": lambda: service.generate_seo_description(project),
    }

    gen = generators.get(body.field)
    if not gen:
        raise HTTPException(400, f"Unknown field: {body.field}")

    try:
        result = gen()
    except Exception as e:
        raise HTTPException(502, f"AI generation failed: {str(e)}")

    return {"text": result, "field": body.field}


# ─── Content Moderation ──────────────────────────────────────────────────────

class ModerateRequest(BaseModel):
    text: str


@router.post("/projects/{project_id}/moderate")
async def moderate_content(
    project_id: str,
    body: ModerateRequest,
    current_user: UserInfo = Depends(get_current_user),
    service: AccoSiteService = Depends(get_accosite_service),
):
    result = service.moderate_text(body.text)
    return result


# ─── Image Upload ────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/images")
async def upload_image(
    project_id: str,
    file: UploadFile = File(...),
    label: str = Query("general"),
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = repo.get(current_user.user_id, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Validate file type
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"File type not allowed: {file.content_type}")

    # Read and save
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 5MB)")

    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"{label}_{uuid.uuid4().hex[:8]}.{ext}"

    images_dir = repo.get_images_dir(current_user.user_id, project_id)
    filepath = os.path.join(images_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    return {"filename": filename, "url": f"/api/v1/accosite/projects/{project_id}/images/{filename}"}


@router.get("/projects/{project_id}/images/{filename}")
async def get_image(
    project_id: str,
    filename: str,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    images_dir = repo.get_images_dir(current_user.user_id, project_id)
    filepath = os.path.join(images_dir, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Image not found")

    from fastapi.responses import FileResponse
    return FileResponse(filepath)


@router.get("/projects/{project_id}/images")
async def list_images(
    project_id: str,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    images_dir = repo.get_images_dir(current_user.user_id, project_id)
    if not os.path.exists(images_dir):
        return []
    files = [f for f in os.listdir(images_dir) if not f.startswith(".")]
    return [{"filename": f, "url": f"/api/v1/accosite/projects/{project_id}/images/{f}"} for f in sorted(files)]


# ─── Preview & Export ────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/preview")
async def preview_website(
    project_id: str,
    token: Optional[str] = Query(None),
    current_user: Optional[UserInfo] = None,
    repo: ProjectRepository = Depends(get_project_repo),
):
    # Allow auth via query param (for iframe embedding) or header
    user_id = None
    if current_user:
        user_id = current_user.user_id
    elif token:
        from api.dependencies import _get_auth_provider
        try:
            user_info = _get_auth_provider().verify_token(token)
            user_id = user_info.user_id
        except Exception:
            raise HTTPException(401, "Invalid token")
    else:
        # In dev mode, allow preview without auth for convenience
        from infrastructure.config import config
        if config.ENV in ("test", "development", "local"):
            user_id = "mock-user-chris-123"
        else:
            raise HTTPException(401, "Authentication required")

    project = repo.get(user_id, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    base_url = f"/api/v1/accosite/projects/{project_id}/images?token={token or 'test-chris'}"
    html = generate_website(project, base_image_url=base_url)
    return HTMLResponse(content=html)


@router.get("/projects/{project_id}/export")
async def export_website(
    project_id: str,
    current_user: UserInfo = Depends(get_current_user),
    repo: ProjectRepository = Depends(get_project_repo),
):
    project = repo.get(current_user.user_id, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    html = generate_website(project, base_image_url="assets")

    # Build ZIP
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("index.html", html)

        images_dir = repo.get_images_dir(current_user.user_id, project_id)
        if os.path.exists(images_dir):
            for filename in os.listdir(images_dir):
                if not filename.startswith("."):
                    filepath = os.path.join(images_dir, filename)
                    zf.write(filepath, f"assets/{filename}")

    buffer.seek(0)
    slug = project.slug or "website"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{slug}-website.zip"'},
    )


# ─── Static Data ─────────────────────────────────────────────────────────────

@router.get("/amenities")
async def get_amenities():
    return AMENITY_CATALOGUE


@router.get("/templates")
async def get_templates():
    return [
        {"id": "tropical-fresh", "name": "Tropical Fresh", "description": "Greens, warm whites, organic shapes"},
        {"id": "modern-minimal", "name": "Modern Minimal", "description": "Clean whites, black accents, high contrast"},
        {"id": "warm-rustic", "name": "Warm & Rustic", "description": "Earthy tones, serif fonts, warm beige"},
        {"id": "luxury-dark", "name": "Luxury Dark", "description": "Deep navy/charcoal, gold accents"},
    ]
