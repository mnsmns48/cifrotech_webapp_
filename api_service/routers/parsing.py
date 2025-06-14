import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import get_vendor_by_url
from api_service.schemas import ParsingRequest, DetailDependenciesUpdate
from config import redis_session
from engine import db

from models import Harvest
from models.vendor import VendorSearchLine, HarvestLine, DetailDependencies
from parsing.logic import parsing_core
from parsing.utils import append_info

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
    harvest_line_query = (select(HarvestLine).where(HarvestLine.harvest_id == harvest_id.id)
                          .order_by(HarvestLine.input_price))
    harvest_line_result = await session.execute(harvest_line_query)
    harvest_lines = harvest_line_result.scalars().all()
    result = {'is_ok': True, 'category': harvest_id.category, 'datestamp': harvest_id.datestamp}
    data = {'data': [line.__dict__ for line in harvest_lines]}
    data = await append_info(session=session, data=data)
    result.update(data)
    return result


@parsing_router.put("/update_parsing_item/{origin}")
async def update_parsing_item(origin: str, data: DetailDependenciesUpdate,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = select(DetailDependencies).where(DetailDependencies.origin == origin)
    result = await session.execute(stmt)
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Запись с таким origin не найдена")
    payload = data.model_dump(exclude_unset=True)
    if not payload:
        return "Данные для изменения не переданы"
    updates = {k: v for k, v in payload.items() if getattr(item, k, None) != v or v is None}
    if not updates:
        return "Нет изменений"
    for k, v in updates.items():
        setattr(item, k, v)
    await session.commit()
    return {"Изменены поля записи": list(updates.keys())}
