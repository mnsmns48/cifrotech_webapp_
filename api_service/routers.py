from io import BytesIO
from fastapi import APIRouter, Request, Depends
from num2words import num2words
from starlette.responses import HTMLResponse, StreamingResponse
from xlsxtpl.writerx import BookWriter

from api_service.schemas import get_receipt_form
from api_users.dependencies.fastapi_users_dep import current_super_user
from config import BASE_DIR

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
