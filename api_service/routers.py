from io import BytesIO
from fastapi import APIRouter, Request, Depends, HTTPException
from num2words import num2words
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse, StreamingResponse
from xlsxtpl.writerx import BookWriter

from api_service.schemas import get_receipt_form, serialize_vendors, VendorSchema
from api_users.dependencies.fastapi_users_dep import current_super_user
from config import BASE_DIR
from engine import db
from models import Vendor

service_router = APIRouter(prefix="/service", dependencies=[Depends(current_super_user)])


@service_router.post("/billrender", response_class=HTMLResponse)
async def submit_link(request: Request, form=Depends(get_receipt_form)):
    xlsx_template = BASE_DIR / "api_service/E1.xlsx"
    with open(xlsx_template, "rb") as template_file:
        file_stream = BytesIO(template_file.read())
        writer = BookWriter(file_stream)
    form_dict = form.dict()
    form_dict.update({'total_by_words': num2words(int(form.total), lang='ru')})
    writer.render_book([form_dict])
    result_stream = BytesIO()
    writer.save(result_stream)
    result_stream.seek(0)
    response = StreamingResponse(result_stream,
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = f"attachment; filename=receipt.xlsx"
    return response


@service_router.get("/vendors")
async def get_vendors(request: Request, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(Vendor))
    vendors = result.scalars().all()
    return serialize_vendors(vendors)


@service_router.post("/vendors")
async def add_vendor(vendor_data: VendorSchema, session: AsyncSession = Depends(db.scoped_session_dependency)):
    new_vendor = Vendor(name=vendor_data.name, source=vendor_data.source, telegram_id=vendor_data.telegram_id)
    session.add(new_vendor)
    await session.commit()
    await session.refresh(new_vendor)
    return {"message": "Поставщик добавлен", "vendor": new_vendor.__dict__}


@service_router.put("/vendors/{vendor_id}")
async def update_vendor(vendor_id: int, vendor_data: VendorSchema,
                        session: AsyncSession = Depends(db.scoped_session_dependency)):
    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Поставщик не найден")
    update_data = {key: value for key, value in vendor_data.model_dump().items() if value is not None and key != "id"}
    for key, value in update_data.items():
        setattr(vendor, key, value)
    await session.commit()
    await session.refresh(vendor)

    return {"message": "Поставщик обновлен", "vendor": vendor.__dict__}


@service_router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    vendor = await session.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Поставщик не найден")
    await session.delete(vendor)
    await session.commit()
    return {"message": "Поставщик удален"}
