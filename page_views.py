from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import HTMLResponse

from core.crud import get_directory
from core.engine import pg_engine

pages_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@pages_router.get("/", response_class=HTMLResponse)
async def get_page(
    request: Request,
    session: AsyncSession = Depends(dependency=pg_engine.scoped_session_dependency),
):
    buttons = await get_directory(session=session, parent=0)
    return templates.TemplateResponse(
        name="index.html", context={"request": request, "buttons": buttons}
    )


@pages_router.get("/{parent}")
async def get_page_p(
    parent: int,
    request: Request,
    session: AsyncSession = Depends(dependency=pg_engine.scoped_session_dependency),
):
    buttons = await get_directory(session=session, parent=parent)
    return templates.TemplateResponse(
        name="index.html", context={"request": request, "buttons": buttons}
    )
