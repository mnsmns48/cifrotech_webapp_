import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_vendor_by_url
from api_service.schemas import ParsingRequest
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
        await redis.publish(data.progress, "data: COUNT=1")
        await asyncio.sleep(0.5)
        await redis.publish(data.progress, "END")
        await pubsub_obj.unsubscribe(data.progress)
        await pubsub_obj.close()
    return parsing_data


@parsing_router.get("/previous_parsing_results/{vsl_id}")
async def get_previous_results(vsl_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
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
        .where(HarvestLine.harvest_id == harvest_id.id)
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
