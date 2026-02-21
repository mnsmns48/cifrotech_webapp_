from datetime import datetime
from typing import List

from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.main import get_info_by_caching, delete_product_stock_items, get_rr_obj, fetch_hubstock_items, \
    update_parsing_line_prices, fetch_parsing_input_price_map
from api_service.s3_helper import get_s3_client, get_http_client_session, sync_images_by_origin

from api_service.schemas import (
    StockHubItemResult, HubLoadingData, OriginsPayload, HubItemTitlePatch, HubItemsChangePriceRequest,
    HubItemsChangePriceResponse, RewardRangeBaseSchema
)
from api_service.schemas.hubstock_schemas import HubLoadingResponse
from engine import db
from models import HUbStock, ProductOrigin, VendorSearchLine, RewardRange
from parsing.utils import cost_process

hubstock_router = APIRouter(tags=['Hub Stock'])


@hubstock_router.get("/fetch_stock_hub_items/{path_id}", response_model=List[StockHubItemResult])
async def fetch_stock_hub_items(
        path_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = (
        select(HUbStock, ProductOrigin, RewardRange, VendorSearchLine)
        .join(ProductOrigin, HUbStock.origin == ProductOrigin.origin)
        .outerjoin(RewardRange, HUbStock.profit_range_id == RewardRange.id)
        .join(VendorSearchLine, HUbStock.vsl_id == VendorSearchLine.id)
        .where(HUbStock.path_id == path_id)
        .order_by(HUbStock.output_price)
    )

    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    origin_ids = [stock.origin for stock, _, _, _ in rows]
    features_map = await get_info_by_caching(session, origin_ids)
    result = list()
    for stock, origin, reward_range, vsl in rows:
        result.append(
            StockHubItemResult(
                origin=stock.origin,
                title=origin.title,
                warranty=stock.warranty,
                input_price=stock.input_price,
                output_price=stock.output_price,
                updated_at=stock.updated_at,
                dt_parsed=vsl.dt_parsed,
                features_title=features_map.get(stock.origin, []),
                profit_range=reward_range
            )
        )
    return result


@hubstock_router.post("/load_items_in_hub", response_model=HubLoadingResponse)
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
        item["profit_range_id"] = item.get("profit_range", {}).get("id")
        item.pop("profit_range", None)
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
    return HubLoadingResponse(status=True, updated_origins=[item.origin for item in payload.stocks])


@hubstock_router.patch("/rename_hubstock_obj_title", response_model=HubItemTitlePatch)
async def rename_hubstock_obj_title(
        patch_data: HubItemTitlePatch, session: AsyncSession = Depends(db.scoped_session_dependency)):
    origin = patch_data.origin
    query = select(ProductOrigin).where(ProductOrigin.origin == origin)
    execute = await session.execute(query)
    obj = execute.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Такого товара нет")
    obj.title = patch_data.new_title
    session.add(obj)
    await session.commit()
    return patch_data


@hubstock_router.patch("/calc_hubstock_items", response_model=List[HubItemsChangePriceResponse])
async def recalc_hubstock_items(
        patch_data: HubItemsChangePriceRequest, session: AsyncSession = Depends(db.scoped_session_dependency)):
    reward_range_obj, profit_range = None, None
    if patch_data.new_profit_range_id:
        reward_range_obj = await get_rr_obj(session, patch_data.new_profit_range_id)
        profit_range = RewardRangeBaseSchema(id=reward_range_obj.id, title=reward_range_obj.title)
    origin_price_map = dict()
    for line in patch_data.price_update:
        origin_price_map[line.origin] = line.new_price
    rows = await fetch_hubstock_items(session, list(origin_price_map.keys()))
    input_price_map = await fetch_parsing_input_price_map(session, list(origin_price_map.keys()))
    result: List[HubItemsChangePriceResponse] = list()
    dt_now_obj = datetime.now()
    parsing_updated_dict = dict()
    for row in rows:
        new_price = origin_price_map.get(row.origin)
        if reward_range_obj:
            new_price = cost_process(row.input_price, reward_range_obj.ranges)
            row.output_price = new_price
            row.profit_range_id = reward_range_obj.id
        else:
            row.output_price = new_price
            row.profit_range_id = None
        row.input_price = input_price_map.get(row.origin)
        row.updated_at = dt_now_obj
        parsing_updated_dict[row.origin] = {"new_price": new_price,
                                            "profit_range_id": profit_range.id if profit_range else None}
        result.append(HubItemsChangePriceResponse(origin=row.origin,
                                                  new_price=new_price,
                                                  updated_at=dt_now_obj,
                                                  profit_range=profit_range))
    session.add_all(rows)
    await update_parsing_line_prices(session, parsing_updated_dict)
    await session.commit()
    return result


@hubstock_router.delete("/delete_stock_items")
async def delete_stock_items_endpoint(payload: OriginsPayload,
                                      session: AsyncSession = Depends(db.scoped_session_dependency)) -> List[int]:
    try:
        deleted_origins = await delete_product_stock_items(session, payload.origins)
        return deleted_origins
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Ошибка при удалении")
