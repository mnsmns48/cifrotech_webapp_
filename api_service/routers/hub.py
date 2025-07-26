from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import RenameRequest, HubPositionPatch, StockHubItem, HubLoadingResult, HubLoadingData
from engine import db
from models import HUbMenuLevel, HUbStock, ProductOrigin, HubLoading, VendorSearchLine

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
    inserted = False

    new_order = list()
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


@hub_router.post("/add_hub_level")
async def add_hub_level(payload: dict, session: AsyncSession = Depends(db.scoped_session_dependency)):
    parent_id = payload.get("parent_id")
    label = payload.get("label", "Новый уровень")
    if parent_id is None:
        raise HTTPException(400, "parent_id обязателен")
    result = await session.execute(
        select(HUbMenuLevel.sort_order)
        .where(HUbMenuLevel.parent_id == parent_id)
        .order_by(HUbMenuLevel.sort_order.desc())
        .limit(1)
    )
    max_order = result.scalar_one_or_none() or 0

    new_level = HUbMenuLevel(parent_id=parent_id, label=label, sort_order=max_order + 1)
    session.add(new_level)
    await session.commit()

    return {"status": "created",
            "id": new_level.id, "label": new_level.label, "parent_id": new_level.parent_id,
            "sort_order": new_level.sort_order}

@hub_router.delete("/delete_hub_level/{level_id}")
async def delete_hub_level(level_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    level = await session.get(HUbMenuLevel, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Уровень не найден")

    result = await session.execute(select(HUbMenuLevel.id).where(HUbMenuLevel.parent_id == level_id).limit(1))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить уровень с дочерними элементами"
        )
    parent_id = level.parent_id
    old_order = level.sort_order
    await session.delete(level)
    await session.execute(
        update(HUbMenuLevel)
        .where(HUbMenuLevel.parent_id == parent_id, HUbMenuLevel.sort_order > old_order)
        .values(sort_order=HUbMenuLevel.sort_order - 1)
    )
    await session.commit()
    return {"status": "deleted", "id": level_id}

@hub_router.get("/fetch_stock_hub_items/{path_id}", response_model=List[StockHubItem])
async def fetch_stock_hub_items(path_id: int,
                                session: AsyncSession = Depends(db.scoped_session_dependency)) -> List[StockHubItem]:
    stmt = (
        select(
            HUbStock.origin, ProductOrigin.title, HUbStock.warranty, HUbStock.output_price, HubLoading.datestamp, HubLoading.url,
        )
        .join(ProductOrigin, HUbStock.origin == ProductOrigin.origin)
        .outerjoin(HubLoading, HUbStock.loading_id == HubLoading.id)
        .where(HUbStock.path_id == path_id).
        order_by(HUbStock.output_price)
    )
    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    items = list()
    for origin, title, warranty, output_price, datestamp, url in rows:
        items.append(
            StockHubItem(
                origin=origin, title=title, warranty=warranty,output_price=output_price, datestamp=datestamp, url=url)
        )
    return items


@hub_router.post("/items_to_hub_loadings", response_model=HubLoadingResult)
async def create_hub_loading(
    payload: HubLoadingData,
    session: AsyncSession = Depends(db.scoped_session_dependency)
):
    line = await session.get(VendorSearchLine, payload.vsl_id)
    if not line:
        raise HTTPException(404, "VendorSearchLine not found")
    hub = HubLoading(url=str(line.url), datestamp=payload.datestamp)
    session.add(hub)
    await session.flush()
    for s in payload.stocks:
        origin = s["origin"]
        existing: HUbStock | None = await session.get(HUbStock, origin)
        if existing:
            existing.loading_id = hub.id
            existing.path_id = s["path_id"]
            existing.warranty = s.get("warranty")
            existing.output_price = s.get("output_price")
        else:
            session.add(
                HUbStock(
                    loading_id = hub.id,
                    origin = origin,
                    path_id = s["path_id"],
                    warranty = s.get("warranty"),
                    output_price = s.get("output_price"),
                )
            )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(400, "Ошибка целостности данных при вставке/обновлении stocks")
    stmt = (
        select(HubLoading)
        .options(selectinload(HubLoading.stocks))
        .filter_by(id=hub.id)
    )
    result = await session.execute(stmt)
    hub_with_stocks = result.scalar_one()
    return HubLoadingResult.model_validate(
        hub_with_stocks,
        from_attributes=True
    )