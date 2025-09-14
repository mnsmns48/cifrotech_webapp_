from datetime import datetime, timezone
from typing import List, Dict, Optional

from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.crud import get_info_by_caching, delete_product_stock_items, get_reward_range_profile
from api_service.s3_helper import get_s3_client, get_http_client_session, sync_images_by_origin

from api_service.schemas import StockHubItemResult, HubLoadingData, OriginsPayload, \
    HubItemChangeRequest, HubItemChangeResponse, ProfitRangeOut
from engine import db
from models import HUbStock, ProductOrigin, VendorSearchLine, RewardRange

hubstock_router = APIRouter(tags=['Hub Stock'])


@hubstock_router.get("/fetch_stock_hub_items/{path_id}", response_model=List[StockHubItemResult])
async def fetch_stock_hub_items(
        path_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = (
        select(HUbStock, ProductOrigin, RewardRange)
        .join(ProductOrigin, HUbStock.origin == ProductOrigin.origin)
        .outerjoin(RewardRange, HUbStock.profit_range_id == RewardRange.id)
        .where(HUbStock.path_id == path_id)
        .order_by(HUbStock.output_price)
    )

    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    origin_ids = [stock.origin for stock, _, _ in rows]
    features_map = await get_info_by_caching(session, origin_ids)
    items = list()
    for stock, origin, reward_range in rows:
        items.append(
            StockHubItemResult(origin=stock.origin,
                               title=origin.title,
                               warranty=stock.warranty,
                               input_price=stock.input_price,
                               output_price=stock.output_price,
                               updated_at=stock.updated_at,
                               dt_parsed=stock.updated_at,
                               features_title=features_map.get(stock.origin, []),
                               profit_range=reward_range)
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


@hubstock_router.post("/update_stock_items", response_model=List[HubItemChangeResponse])
async def update_stock_items(
        payload: HubItemChangeRequest,
        session: AsyncSession = Depends(db.scoped_session_dependency)):
    def build_response(
            orig: int, prod: ProductOrigin,
            stck: HUbStock, upd_at: Optional[datetime],
            reward_range: Optional[RewardRange]) -> HubItemChangeResponse:
        return (
            HubItemChangeResponse(origin=orig, new_title=str(prod.title),
                                  new_price=stck.output_price or 0.0,
                                  updated_at=upd_at,
                                  profit_range=ProfitRangeOut(
                                      id=reward_range.id, title=reward_range.title) if reward_range else None)
        )

    all_origins = set()
    if payload.title_updates:
        all_origins.update(payload.title_updates.keys())
    if payload.price_updates:
        all_origins.update(p.origin for p in payload.price_updates)

    if not all_origins:
        raise HTTPException(status_code=400, detail="Нет данных для изменения")

    products_query = select(ProductOrigin).where(ProductOrigin.origin.in_(all_origins))
    result_products = await session.execute(products_query)
    product_rows = result_products.scalars().all()

    products_by_origin: Dict[int, ProductOrigin] = {}
    for product in product_rows:
        origin_key = product.origin
        products_by_origin[origin_key] = product

    stocks_query = (select(HUbStock)
                    .where(HUbStock.origin.in_(all_origins)).options(selectinload(HUbStock.reward_range)))
    result_stocks = await session.execute(stocks_query)
    stock_rows = result_stocks.scalars().all()

    stocks_by_origin: Dict[int, HUbStock] = dict()
    for stock in stock_rows:
        origin_key = stock.origin
        stocks_by_origin[origin_key] = stock

    reward_range_obj = None
    if payload.price_updates and len(payload.price_updates) > 1:
        if payload.new_profit_range_id is None:
            raise HTTPException(status_code=400,
                                detail="При массовом изменении цены необходимо указать profit_range_id")
        reward_range_obj = await get_reward_range_profile(session, payload.new_profit_range_id)

    updated_items: List[HubItemChangeResponse] = list()

    if payload.title_updates:
        for origin, new_title in payload.title_updates.items():
            product = products_by_origin.get(origin)
            stock = stocks_by_origin.get(origin)
            if not product or not stock:
                continue

            if product.title.strip() != new_title.strip():
                product.title = new_title.strip()
                session.add(product)

            updated_items.append(build_response(origin, product, stock, None, stock.reward_range))

    if payload.price_updates:
        for update in payload.price_updates:
            origin = update.origin
            new_price = update.new_price

            stock = stocks_by_origin.get(origin)
            product = products_by_origin.get(origin)
            if not stock or not product:
                continue

            updated_at = None
            if stock.output_price != new_price:
                stock.output_price = new_price
                stock.updated_at = updated_at = datetime.now(timezone.utc)
                stock.profit_range_id = reward_range_obj.id if reward_range_obj else None
                session.add(stock)
            updated_items.append(build_response(origin, product, stock, updated_at, reward_range_obj))

    await session.commit()
    return updated_items


@hubstock_router.delete("/delete_stock_items")
async def delete_stock_items_endpoint(payload: OriginsPayload,
                                      session: AsyncSession = Depends(db.scoped_session_dependency)) -> bool:
    try:
        await delete_product_stock_items(session, payload.origins)
        return True
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении")
