"""
Item API Routes
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List

from modules.item_manager.models import Item
from modules.item_manager.repository import ItemRepository
from modules.item_manager.exceptions import ItemNotFoundError
from api.schemas.items import ItemCreate, ItemUpdate, ItemResponse, ItemListResponse
from api.dependencies import get_item_repository

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemResponse, status_code=201)
async def create_item(
    data: ItemCreate,
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Create a new item.
    """
    # TODO: Get owner_id from auth context
    owner_id = "demo-user"

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
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    List items with optional filters.
    """
    # TODO: Get owner_id from auth context
    owner_id = "demo-user"

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
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Get a single item by ID.
    """
    item = repo.find_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # TODO: Check owner_id matches auth context

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
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Update an item.
    """
    item = repo.find_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # TODO: Check owner_id matches auth context

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
    repo: ItemRepository = Depends(get_item_repository)
):
    """
    Soft-delete an item.
    """
    item = repo.find_by_id(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # TODO: Check owner_id matches auth context

    repo.delete(item_id, hard=False)
    return None
