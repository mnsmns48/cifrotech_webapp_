import asyncio

from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.api_req import get_items_by_brand
from api_service.crud import get_vendor_by_url
from api_service.schemas import ParsingRequest, ProductOriginUpdate
from config import redis_session
from engine import db

from models import Harvest, HarvestLine, ProductOrigin
from models.vendor import VendorSearchLine
from parsing.logic import parsing_core, append_info

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/start_parsing")
async def go_parsing(data: ParsingRequest,
                     redis=Depends(redis_session),
                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    pubsub_obj = redis.pubsub()
    vendor = await get_vendor_by_url(session=session, url=data.vsl_url)
    try:
        parsing_data: dict = await parsing_core(redis, data, vendor, session, vendor.function)
        if len(parsing_data.get('data')) > 0:
            parsing_data.update({'is_ok': True})
    finally:
        await redis.publish(data.progress, "data: COUNT=20")
        await asyncio.sleep(0.5)
        await redis.publish(data.progress, "END")
        await pubsub_obj.unsubscribe(data.progress)
        await pubsub_obj.close()
    return parsing_data


@parsing_router.get("/previous_parsing_results/{vsl_id}")
async def get_previous_results(vsl_id: int, redis=Depends(redis_session),
                               session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl_exists_query = select(VendorSearchLine).where(VendorSearchLine.id == vsl_id)
    vsl_exists_result = await session.execute(vsl_exists_query)
    if not vsl_exists_result.scalars().first():
        raise HTTPException(status_code=404, detail="Vendor_search_line с таким ID не найден")
    harvest_query = select(Harvest).where(Harvest.vendor_search_line_id == vsl_id)
    harvest_result = await session.execute(harvest_query)
    harvest_id = harvest_result.scalars().first()
    if not harvest_id:
        return {"response": "not found", "is_ok": False,
                "message": "Предыдущих результатов нет, соберите данные заново"}
    harvest_line_query = (
        select(HarvestLine, ProductOrigin)
        .join(ProductOrigin, HarvestLine.origin == ProductOrigin.origin)
        .where(and_(
            HarvestLine.harvest_id == harvest_id.id,
            ProductOrigin.is_deleted.is_(False)),
        )
        .order_by(HarvestLine.input_price)
    )
    harvest_line_result = await session.execute(harvest_line_query)
    harvest_lines = harvest_line_result.all()
    result = {'is_ok': True, 'category': harvest_id.category, 'datestamp': harvest_id.datestamp}
    joined_data = list()
    for harvest_line, product_origin in harvest_lines:
        combined_dict = jsonable_encoder(harvest_line)
        combined_dict.update(jsonable_encoder(product_origin))
        joined_data.append(combined_dict)
    result['data'] = await append_info(session=session, data_lines=joined_data)
    return result


@parsing_router.put("/update_parsing_item/{origin}")
async def update_parsing_item(origin: int, data: ProductOriginUpdate,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = select(ProductOrigin).where(ProductOrigin.origin == int(origin))
    result = await session.execute(stmt)
    product_origin = result.scalar_one_or_none()

    if product_origin is None:
        raise HTTPException(status_code=404, detail="ProductOrigin not found")

    if product_origin.title != data.title:
        product_origin.title = data.title
        await session.commit()
        return {"updated": data.title}


@parsing_router.post("/delete_parsing_items/")
async def delete_parsing_items(origins: list[int], session: AsyncSession = Depends(db.scoped_session_dependency)):
    if not origins:
        raise HTTPException(422, detail="Список origin пуст")
    origin_exist = select(ProductOrigin.origin).where(ProductOrigin.origin.in_(origins))
    result = (await session.execute(origin_exist)).scalars().all()
    if not result:
        raise HTTPException(404, detail="Переданные origin не найдены")
    stmt = update(ProductOrigin).where(ProductOrigin.origin.in_(result)).values(is_deleted=True)
    await session.execute(stmt)
    await session.commit()


@parsing_router.get("/update_parsing_item_dependency/{origin}")
async def update_parsing_item_dependency(origin: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = select(ProductOrigin.title).where(ProductOrigin.origin == origin)
    result = await session.execute(stmt)
    title = result.scalar_one_or_none()
    if not title:
        raise HTTPException(status_code=404, detail="origin не найден")
    async with ClientSession() as client_session:
        data = await get_items_by_brand(client_session, title)
    if data is None:
        raise HTTPException(status_code=502, detail="Нет данных")

    return {"items": data}
