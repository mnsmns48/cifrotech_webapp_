from io import BytesIO

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from num2words import num2words
from starlette.responses import HTMLResponse, StreamingResponse
from xlsxtpl.writerx import BookWriter

from aservice88.schemas import take_form_result
from cfg import BASE_DIR

aservice88 = APIRouter(prefix="/aservice88")
templates = Jinja2Templates(directory=f"{BASE_DIR}/aservice88/tmplts")


@aservice88.get("/tpl")
async def bill_editor(request: Request):
    context = {"request": request}
    return templates.TemplateResponse(name="cash_receipt_editor.html", context=context)


@aservice88.post("/submit", response_class=HTMLResponse)
async def submit_link(request: Request, form=Depends(take_form_result)):
    xlsx_template = BASE_DIR / "aservice88/tmplts/E1.xlsx"
    with open(xlsx_template, "rb") as template_file:
        file_stream = BytesIO(template_file.read())
        writer = BookWriter(file_stream)
    total: int = form['receipt_qty'] * form['receipt_price']
    form.update({'total_by_words': num2words(int(total), lang='ru')})
    writer.render_book([form])
    result_stream = BytesIO()
    writer.save(result_stream)
    result_stream.seek(0)
    filename = form['receipt_product'].replace(' ', '_')
    response = StreamingResponse(result_stream,
                                 media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response.headers["Content-Disposition"] = f"attachment; filename=receipt-{filename[:25]}.xlsx"
    return response
