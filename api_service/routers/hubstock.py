from datetime import datetime, timezone
from typing import List

from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_info_by_caching, delete_product_stock_items
from api_service.routers import hub_router
from api_service.s3_helper import get_s3_client, get_http_client_session, sync_images_by_origin

from api_service.schemas import StockHubItemResult, HubLoadingData, HubItemChangeScheme, OriginsPayload
from engine import db
from models import HUbStock, ProductOrigin, VendorSearchLine

hubstock_router = APIRouter(tags=['Hub Stock'])


@hubstock_router.get("/fetch_stock_hub_items/{path_id}", response_model=List[StockHubItemResult])
async def fetch_stock_hub_items(
        path_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = (select(HUbStock, ProductOrigin).join(ProductOrigin, HUbStock.origin == ProductOrigin.origin)
            .where(HUbStock.path_id == path_id).order_by(HUbStock.output_price))
    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    origin_ids = [stock.origin for stock, _ in rows]
    features_map = await get_info_by_caching(session, origin_ids)
    items = list()
    for stock, origin in rows:
        items.append(
            StockHubItemResult(origin=stock.origin,
                               title=origin.title,
                               warranty=stock.warranty,
                               input_price=stock.input_price,
                               output_price=stock.output_price,
                               updated_at=stock.updated_at,
                               dt_parsed=stock.updated_at,
                               features_title=features_map.get(stock.origin, []),
                               profit_range_id=stock.profit_range_id)
        )
    return items


@hubstock_router.post("/load_items_in_hub")
async def create_hub_loading(payload: HubLoadingData,
                             session: AsyncSession = Depends(db.scoped_session_dependency),
                             s3_client: AioBaseClient = Depends(get_s3_client),
                             cl_session: ClientSession = Depends(get_http_client_session)):
    vsl = await session.get(VendorSearchLine, payload.vsl_id)
    if not vsl or not vsl.dt_parsed:
        raise HTTPException(status_code=400, detail="Такой vsl_id не найден")

    hub_stock_values = [stock_item.model_dump() for stock_item in payload.stocks]
    for item in hub_stock_values:
        item["vsl_id"] = payload.vsl_id
        item["updated_at"] = vsl.dt_parsed
        item["added_at"] = datetime.now()
    insert_stmt = insert(HUbStock).values(hub_stock_values)
    upsert_stmt = insert_stmt.on_conflict_do_update(index_elements=["origin", "path_id"],
                                                    set_={"warranty": insert_stmt.excluded.warranty,
                                                          "input_price": insert_stmt.excluded.input_price,
                                                          "output_price": insert_stmt.excluded.output_price,
                                                          "updated_at": insert_stmt.excluded.updated_at})
    await session.execute(upsert_stmt)
    await session.commit()
    for item in payload.stocks:
        await sync_images_by_origin(item.origin, session, s3_client, cl_session)
    return {"status": True}


@hubstock_router.patch("/rename_or_change_price_stock_item")
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
        stock.profit_range_id = None
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
