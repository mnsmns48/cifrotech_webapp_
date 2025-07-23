from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import RenameRequest, HubPositionPatch
from engine import db
from models import HUbMenuLevel

hub_router = APIRouter(tags=['Hub'])


@hub_router.get("/initial_hub_levels")
async def get_hub_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(HUbMenuLevel))
    items = result.scalars().all()
    return items

@hub_router.patch("/rename_hub_level")
async def rename_hub_level_item(payload: RenameRequest, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(HUbMenuLevel).where(HUbMenuLevel.id == payload.id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Узел не найден")
    if item.label == payload.new_label:
        return {
            "status": "skipped", "message": "Имя совпадает — изменений не требуется", "id": item.id, "label": item.label
        }
    item.label = payload.new_label
    await session.commit()
    await session.refresh(item)
    return {"status": "renamed", "id": item.id, "new_label": item.label}

@hub_router.patch("/change_hub_item_position")
async def change_hub_item_position(patch: HubPositionPatch, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(HUbMenuLevel).where(HUbMenuLevel.id == patch.id))
    moved = result.scalar_one_or_none()
    if not moved:
        raise HTTPException(status_code=404, detail="Узел не найден")

    siblings_result = await session.execute(
        select(HUbMenuLevel)
        .where(HUbMenuLevel.parent_id == patch.parent_id, HUbMenuLevel.id != patch.id)
        .order_by(HUbMenuLevel.sort_order)
    )
    siblings = list(siblings_result.scalars())
    new_order = list()
    inserted = False

    for sibling in siblings:
        new_order.append(sibling)
        if sibling.id == patch.after_id:
            new_order.append(moved)
            inserted = True

    if not inserted:
        new_order.insert(0, moved)

    index_counter = 0
    for item in new_order:
        item.sort_order = index_counter
        item.parent_id = patch.parent_id
        index_counter += 1

    await session.commit()
    await session.refresh(moved)

    return {"status": "updated", "id": moved.id, "parent_id": moved.parent_id, "sort_order": moved.sort_order}
