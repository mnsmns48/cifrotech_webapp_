from datetime import datetime
from io import BytesIO
from fastapi import Depends, APIRouter, Path, HTTPException
from num2words import num2words
from openpyxl.styles import Alignment
from openpyxl.workbook import Workbook
from sqlalchemy import select, join
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from starlette.responses import HTMLResponse, StreamingResponse
from xlsxtpl.writerx import BookWriter
from api_service.schemas import get_receipt_form
from config import BASE_DIR
from engine import db
from models import HarvestLine, ProductOrigin

printer_router = APIRouter(tags=['Service-Bill-Printer'])


@printer_router.post("/billrender", response_class=HTMLResponse)
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


# @printer_router.get("/get_price_excel/{vsl_id}")
# async def export_harvest_to_excel(vsl_id: int = Path(...), session: AsyncSession = Depends(db.scoped_session_dependency)):
#     dt_obj = datetime.now().strftime("%Y_%m_%d___%H_%M_%S")
#     try:
#         query_one = (
#             select(Harvest).where(Harvest.vendor_search_line_id == vsl_id).order_by(Harvest.datestamp.desc()).limit(1))
#         result = await session.execute(query_one)
#         harvest: Harvest | None = result.scalar_one_or_none()
#     except SQLAlchemyError:
#         raise HTTPException(500, "Ошибка доступа к базе данных")
#     if not harvest:
#         raise HTTPException(404, f"Сбор данных для vslId={vsl_id} не найден")
#     query_two = (select(ProductOrigin.title, HarvestLine.warranty, HarvestLine.output_price)
#                  .select_from(
#         HarvestLine.__table__.join(ProductOrigin.__table__, HarvestLine.origin == ProductOrigin.origin))
#                  .where(HarvestLine.harvest_id == harvest.id).order_by(HarvestLine.output_price))
#     rows = (await session.execute(query_two)).all()
#     wb = Workbook()
#     ws = wb.active
#     ws.title = f"h_{harvest.id}_by_cifrohub"
#     for title, warranty, output_price in rows:
#         ws.append([title, warranty or "", output_price if output_price is not None else ""])
#     for row in ws.iter_rows(min_row=1, min_col=2, max_col=4, max_row=ws.max_row):
#         for cell in row:
#             cell.alignment = Alignment(horizontal="center", vertical="center")
#     for column_cells in ws.columns:
#         length = max(len(str(cell.value or "")) for cell in column_cells)
#         ws.column_dimensions[column_cells[0].column_letter].width = length + 2
#     stream = BytesIO()
#     wb.save(stream)
#     stream.seek(0)
#     filename = f"products_offer_{harvest.id}_by_cifrohub_{dt_obj}.xlsx"
#     headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
#     return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                              headers=headers)
