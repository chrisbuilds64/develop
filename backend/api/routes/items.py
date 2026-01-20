"""
Item API Routes

Compliant with REQ-000 Infrastructure Standards.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List

from modules.item_manager.models import Item
from modules.item_manager.repository import ItemRepository
from modules.item_manager.exceptions import ItemNotFoundError
from api.schemas.items import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from api.dependencies import get_item_repository, get_current_user
from adapters.auth import UserInfo
from infrastructure.logging import get_logger

router = APIRouter(prefix="/items", tags=["items"])
logger = get_logger()


@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(
    data: ItemCreate,
    current_user: UserInfo = Depends(get_current_user),
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Create a new item.

    Requires authentication via Bearer token.
    """
    owner_id = current_user.user_id
    logger.info("item_create_start", owner_id=owner_id, content_type=data.content_type)

    item = Item(
        owner_id=owner_id,
        label=data.label,
        content_type=data.content_type,
        payload=data.payload,
        tags=data.tags
    )

    saved = repo.save(item)

    return ItemResponse(
        id=saved.id,
        owner_id=saved.owner_id,
        label=saved.label,
        content_type=saved.content_type,
        payload=saved.payload,
        tags=saved.tags,
        created_at=saved.created_at,
        updated_at=saved.updated_at
    )


@router.get("", response_model=ItemListResponse)
async def list_items(
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: UserInfo = Depends(get_current_user),
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    List items with optional filters.

    Requires authentication via Bearer token.
    Returns only items owned by the authenticated user.
    """
    owner_id = current_user.user_id
    logger.debug("item_list_start", owner_id=owner_id, content_type=content_type)

    # Parse tags
    tag_list = None
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    items = repo.find_all(
        owner_id=owner_id,
        content_type=content_type,
        tags=tag_list,
        limit=limit,
        offset=offset
    )

    return ItemListResponse(
        items=[
            ItemResponse(
                id=item.id,
                owner_id=item.owner_id,
                label=item.label,
                content_type=item.content_type,
                payload=item.payload,
                tags=item.tags,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            for item in items
        ],
        total=len(items),  # TODO: Separate count query for pagination
        limit=limit,
        offset=offset
    )


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    current_user: UserInfo = Depends(get_current_user),
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Get a single item by ID.

    Requires authentication via Bearer token.
    Only returns item if owned by authenticated user.
    """
    item = repo.find_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify ownership
    if item.owner_id != current_user.user_id:
        logger.warning("item_access_denied", item_id=item_id, owner_id=item.owner_id, requester_id=current_user.user_id)
        raise HTTPException(status_code=404, detail="Item not found")

    return ItemResponse(
        id=item.id,
        owner_id=item.owner_id,
        label=item.label,
        content_type=item.content_type,
        payload=item.payload,
        tags=item.tags,
        created_at=item.created_at,
        updated_at=item.updated_at
    )


@router.put("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    data: ItemUpdate,
    current_user: UserInfo = Depends(get_current_user),
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Update an item.

    Requires authentication via Bearer token.
    Only updates item if owned by authenticated user.
    """
    item = repo.find_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify ownership
    if item.owner_id != current_user.user_id:
        logger.warning("item_update_denied", item_id=item_id, owner_id=item.owner_id, requester_id=current_user.user_id)
        raise HTTPException(status_code=404, detail="Item not found")

    # Update fields if provided
    if data.label is not None:
        item.label = data.label
    if data.content_type is not None:
        item.content_type = data.content_type
    if data.payload is not None:
        item.payload = data.payload
    if data.tags is not None:
        item.tags = data.tags

    updated = repo.update(item)

    return ItemResponse(
        id=updated.id,
        owner_id=updated.owner_id,
        label=updated.label,
        content_type=updated.content_type,
        payload=updated.payload,
        tags=updated.tags,
        created_at=updated.created_at,
        updated_at=updated.updated_at
    )


@router.delete("/{item_id}", status_code=204)
async def delete_item(
    item_id: str,
    current_user: UserInfo = Depends(get_current_user),
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Soft-delete an item.

    Requires authentication via Bearer token.
    Only deletes item if owned by authenticated user.
    """
    item = repo.find_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Verify ownership
    if item.owner_id != current_user.user_id:
        logger.warning("item_delete_denied", item_id=item_id, owner_id=item.owner_id, requester_id=current_user.user_id)
        raise HTTPException(status_code=404, detail="Item not found")

    repo.delete(item_id, hard=False)
    logger.info("item_deleted", item_id=item_id, owner_id=current_user.user_id)
    return None
