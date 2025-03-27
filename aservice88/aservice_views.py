from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from starlette.responses import HTMLResponse

from aservice88.schemas import take_form_result
from cfg import BASE_DIR

aservice88 = APIRouter(prefix="/aservice88")
templates = Jinja2Templates(directory=f"{BASE_DIR}/aservice88/tmplts")


@aservice88.get("/tpl")
async def bill_editor(request: Request):
    context = {"request": request}
    return templates.TemplateResponse(name="cash_receipt_editor.html", context=context)

@aservice88.post("/submit", response_class=HTMLResponse)
async def submit_link(request: Request, form = Depends(take_form_result)):
    print(form)
    return templates.TemplateResponse(name="cash_receipt_editor.html", context = {"request": request})
