from io import BytesIO

from fastapi import Depends, APIRouter
from num2words import num2words
from starlette.requests import Request
from starlette.responses import HTMLResponse, StreamingResponse
from xlsxtpl.writerx import BookWriter
from api_service.schemas import get_receipt_form
from config import BASE_DIR

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
