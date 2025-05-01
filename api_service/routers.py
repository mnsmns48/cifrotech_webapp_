from io import BytesIO
from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from num2words import num2words
from starlette.responses import HTMLResponse, StreamingResponse
from xlsxtpl.writerx import BookWriter

from api_service.schemas import take_form_result
from api_users.dependencies.fastapi_users_dep import current_super_user
from config import BASE_DIR
from utils import all_css

service_router = APIRouter(prefix="/service", dependencies=[Depends(current_super_user)])
templates = Jinja2Templates(directory=f"{BASE_DIR}/api_service/templates")


@service_router.get("/bill_editor")
async def bill_editor(request: Request):
    context = {"request": request}
    context.update(all_css)
    return templates.TemplateResponse(name="cash_receipt_editor.html", context=context)


@service_router.post("/billsubmit", response_class=HTMLResponse)
async def submit_link(request: Request, form=Depends(take_form_result)):
    xlsx_template = BASE_DIR / "api_service/E1.xlsx"
    with open(xlsx_template, "rb") as template_file:
        file_stream = BytesIO(template_file.read())
        writer = BookWriter(file_stream)
    total: int = form['receipt_qty'] * form['receipt_price']
    form.update({'total_by_words': num2words(int(total), lang='ru')})
    writer.render_book([form])
    result_stream = BytesIO()
    writer.save(result_stream)
    result_stream.seek(0)
    response = StreamingResponse(result_stream,
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = f"attachment; filename=receipt.xlsx"
    return response
