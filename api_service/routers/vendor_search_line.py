import asyncio
import uuid
from asyncio import Queue

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy import select
from starlette.responses import StreamingResponse

from api_service.schemas import VendorSearchLineSchema
from api_service.utils import update_instance_fields
from engine import db
from models.vendor import Vendor_search_line
from sqlalchemy.ext.asyncio import AsyncSession

vendor_search_line_router = APIRouter(tags=['Service-Vendors-Search-Line'])



@vendor_search_line_router.get("/get_vsl/{vendor_id}")
async def get_vendors(request: Request, vendor_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(
        select(Vendor_search_line).filter(Vendor_search_line.vendor_id == vendor_id).order_by(Vendor_search_line.id))
    vendor_search_lines = list()
    for vsl in result.scalars().all():
        vendor_search_lines.append(VendorSearchLineSchema.cls_validate(vsl))
    return {"vsl": vendor_search_lines}


@vendor_search_line_router.post("/create_vsl/{vendor_id}")
async def create_vendor_search_line(request: Request, vendor_id: int, vsl_data: VendorSearchLineSchema,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    existing_vsl = await session.execute(
        select(Vendor_search_line).where(
            (Vendor_search_line.title == vsl_data.title) | (Vendor_search_line.url == vsl_data.url)))
    existing_vsl = existing_vsl.scalar()
    if existing_vsl:
        raise HTTPException(status_code=409, detail="Vendor Search Line with this title or URL already exists")
    new_vsl = Vendor_search_line(**VendorSearchLineSchema.cls_validate(vsl_data, exclude_id=True))
    session.add(new_vsl)
    await session.commit()
    await session.refresh(new_vsl)
    return {"vsl": VendorSearchLineSchema.cls_validate(new_vsl)}


@vendor_search_line_router.put("/update_vsl/{vsl_id}")
async def update_vendor_search_line(request: Request, vsl_id: int, vsl_data: VendorSearchLineSchema,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(Vendor_search_line, vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="VendorSearchLine not found")
    update_data = VendorSearchLineSchema.cls_validate(vsl_data, exclude_id=True)
    await update_instance_fields(vsl, update_data, session)
    return {"result": f"Vendor Search Line {vsl.id} updated"}


@vendor_search_line_router.delete("/delete_vsl/{vsl_id}")
async def delete_vendor_search_line(vsl_id: int,
                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(Vendor_search_line, vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="Vendor Search Line not found")
    await session.delete(vsl)
    await session.commit()
    return {"result": f"Vendor Search Line {vsl_id} deleted"}


# @vendor_search_line_router.post("/pars_me")
# async def parsing_data(request: Request, data: ParsingRequest,
#                        session: AsyncSession = Depends(db.scoped_session_dependency)):
#     playwright, browser, page = await run_browser()
#
#     async def process(playwright, browser, page):
#         result = await session.execute(
#             select(Vendor)
#             .options(selectinload(Vendor.search_lines))
#             .where(Vendor.search_lines.any(Vendor_search_line.url == data.url))
#         )
#         vendor = result.scalars().first()
#
#         if not vendor:
#             await progress_queue.put("Vendor not found")
#             await progress_queue.put(None)
#             return
#
#         await progress_queue.put("Vendor найден")
#
#         vendor_data = VendorSchema.cls_validate(vendor, exclude_id=True)
#         vendor_data["search_lines"] = [VendorSearchLineSchema.cls_validate(sl, exclude_id=True) for sl in
#                                        vendor.search_lines]
#
#         await progress_queue.put("Vendor данные обработаны")
#         html = await open_page(page, url='https://mail.ru')
#         await progress_queue.put("HTML загружен")
#         await progress_queue.put(str(vendor_data))
#         await progress_queue.put(None)
#         await browser.close()
#         await playwright.stop()
#
#     asyncio.create_task(process(playwright, browser, page))
#     return {"status": "Парсинг запущен"}


class ProgressManager:
    def __init__(self):
        self.progress = 0
        self.total_steps = 5
        self.queue = Queue()

    async def update_progress(self, message: str):
        await self.queue.put(message)
        self.progress += 1

        if self.progress >= self.total_steps:
            await self.queue.put("END")

    async def event_stream(self):
        yield f"data: COUNT={self.total_steps}\n\n"

        while True:
            message = await self.queue.get()
            if message == "END":
                yield "data: END\n\n"
                self.queue = Queue()
                self.progress = 0
                break
            yield f"data: {message}\n\n"

#
# @vendor_search_line_router.post("/pars_me")
# async def parsing_data(data: ParsingRequest):
#     request_id = str(uuid.uuid4())
#     channel = f"progress:{request_id}"
#
#     async def process():
#         await redis_client.setex(request_id, 600, data.url)
#         await asyncio.sleep(15)
#         await redis_client.publish(channel, "data: COUNT=9")
#         await redis_client.publish(channel, "Парсинг начался")
#         for i in range(1, 6):
#             await asyncio.sleep(5)
#             await redis_client.publish(channel, f"Шаг {i} выполнен")
#         await asyncio.sleep(60)
#         final_result = "Основной результат парсинга: данные собраны успешно через 10 секунд."
#         await redis_client.publish(channel, final_result)
#         await redis_client.publish(channel, "data: END")
#
#     asyncio.create_task(process())
#     return {"request_id": request_id}
#
#

#
#
# @vendor_search_line_router.get("/result/{request_id}")
# async def get_result(request_id: str):
#     result = await redis_client.get(name=request_id)
#     return {'result': result}
