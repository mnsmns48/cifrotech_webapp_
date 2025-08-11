from datetime import datetime, timezone
from typing import List

from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.crud import get_info_by_caching, delete_product_stock_items
from api_service.routers.s3_helper import get_s3_client, get_http_client_session, sync_images_by_origin
from api_service.schemas import RenameRequest, HubPositionPatch, StockHubItemResult, HubLoadingData, \
    HubItemChangeScheme, OriginsPayload
from engine import db
from models import HUbMenuLevel, HUbStock, ProductOrigin, HubLoading, VendorSearchLine, ProductFeaturesLink

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
async def change_hub_item_position(patch: HubPositionPatch,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
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


@hub_router.get("/fetch_stock_hub_items/{path_id}", response_model=List[StockHubItemResult])
async def fetch_stock_hub_items(path_id: int,
                                session: AsyncSession = Depends(db.scoped_session_dependency)) -> List[
    StockHubItemResult]:
    stmt = (select(
        HUbStock.origin,
        ProductOrigin.title,
        HUbStock.warranty,
        HUbStock.input_price,
        HUbStock.output_price,
        HUbStock.updated_at,
        HubLoading.dt_parsed,
        HubLoading.url)
            .join(ProductOrigin, HUbStock.origin == ProductOrigin.origin)
            .outerjoin(HubLoading, HUbStock.loading_id == HubLoading.id)
            .where(HUbStock.path_id == path_id).
            order_by(HUbStock.output_price)
            )
    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    origin_ids = [row[0] for row in rows]
    features_map = await get_info_by_caching(session, origin_ids)

    items = list()
    for origin, title, warranty, input_price, output_price, updated_at, dt_parsed, url in rows:
        items.append(
            StockHubItemResult(
                origin=origin,
                title=title,
                warranty=warranty,
                input_price=input_price,
                output_price=output_price,
                updated_at=updated_at,
                dt_parsed=dt_parsed,
                url=url,
                features_title=features_map.get(origin, []))
        )
    return items


@hub_router.post("/items_to_hub_loadings")
async def create_hub_loading(payload: HubLoadingData, session: AsyncSession = Depends(db.scoped_session_dependency),
                             s3_client: AioBaseClient = Depends(get_s3_client),
                             cl_session: ClientSession = Depends(get_http_client_session)):
    origins = [s.get("origin") for s in payload.stocks]
    stmt = select(HUbStock).options(selectinload(HUbStock.hub_loading)).where(HUbStock.origin.in_(origins))
    result = await session.execute(stmt)
    existing_stocks = result.scalars().all()
    existing_map = {stock.origin: stock for stock in existing_stocks}

    reuse_loading_id = None
    for stock in existing_stocks:
        hub = stock.hub_loading
        if hub and hub.dt_parsed == payload.dt_parsed:
            reuse_loading_id = hub.id
            break

    try:
        if reuse_loading_id is None:
            line = await session.get(VendorSearchLine, payload.vsl_id)
            if line is None:
                raise HTTPException(404, "VendorSearchLine not found")

            hub = HubLoading(url=str(line.url), dt_parsed=payload.dt_parsed)
            session.add(hub)
            await session.flush()
            reuse_loading_id = hub.id

        for s in payload.stocks:
            origin = s.get("origin")
            await sync_images_by_origin(origin, session, s3_client, cl_session)

            stock = existing_map.get(origin)
            if stock:
                stock.loading_id = reuse_loading_id
                stock.path_id = s.get("path_id", stock.path_id)
                stock.warranty = s.get("warranty", stock.warranty)
                stock.input_price = s.get("input_price", stock.input_price)
                stock.output_price = s.get("output_price", stock.output_price)
                stock.updated_at = payload.dt_parsed
            else:
                session.add(HUbStock(
                    loading_id=reuse_loading_id,
                    origin=origin,
                    path_id=s.get("path_id"),
                    warranty=s.get("warranty"),
                    input_price=s.get("input_price"),
                    output_price=s.get("output_price"),
                    updated_at=payload.dt_parsed
                ))

        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(400, "Ошибка при создании или обновлении записей")

    return {"result": "ok"}


@hub_router.patch("/rename_or_change_price_stock_item")
async def rename_or_change_price_stock_item(patch: HubItemChangeScheme,
                                            session: AsyncSession = Depends(db.scoped_session_dependency)):
    result_origin = await session.execute(select(ProductOrigin).where(ProductOrigin.origin == patch.origin))
    product = result_origin.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="ProductOrigin не найден")

    result_stock = await session.execute(select(HUbStock).where(HUbStock.origin == patch.origin))
    stock = result_stock.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="HUbStock не найден")

    title_changed, price_changed = False, False

    if patch.title.strip() != product.title:
        product.title = patch.title.strip()
        title_changed = True

    if patch.new_price != stock.output_price:
        stock.output_price = patch.new_price
        stock.updated_at = datetime.now(timezone.utc)
        price_changed = True

    to_update = list()
    if title_changed:
        to_update.append(product)
    if price_changed:
        to_update.append(stock)

    if to_update:
        session.add_all(to_update)
        await session.commit()

    return {"origin": patch.origin,
            "updated": price_changed,
            "new_title": product.title,
            "new_price": stock.output_price,
            "updated_at": stock.updated_at if price_changed else None}


@hub_router.delete("/delete_stock_items")
async def delete_stock_items_endpoint(payload: OriginsPayload,
                                      session: AsyncSession = Depends(db.scoped_session_dependency)) -> bool:
    try:
        await delete_product_stock_items(session, payload.origins)
        return True
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении")


