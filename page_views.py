from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud import get_directory, get_product_list, description, get_parent_path
from core.engine import pg_engine, phones_engine

pages_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@pages_router.get("/")
async def get_page(
        request: Request,
        session_pg: AsyncSession = Depends(dependency=pg_engine.scoped_session_dependency),
):
    response = await get_directory(session_pg=session_pg, parent=0)
    return templates.TemplateResponse(
        name="menu.html",
        context={"request": request, "data": response.get('product_list')}
    )


@pages_router.get("/{parent}")
async def get_page_parent(
        parent: int,
        request: Request,
        session_pg: AsyncSession = Depends(pg_engine.scoped_session_dependency),
        session_desc: AsyncSession = Depends(dependency=phones_engine.scoped_session_dependency)
):
    dir_response = await get_directory(session_pg=session_pg, parent=parent)
    if dir_response.get('destination_folder'):
        data_response = await get_product_list(session_pg=session_pg, session_desc=session_desc, parent=parent)
        menu_buttons = await get_parent_path(session_pg=session_pg, code=parent)
        context = {"request": request, "data": data_response, 'menu_buttons': menu_buttons}
        return templates.TemplateResponse(name="product.html", context=context)
    else:
        context = {"request": request, "data": dir_response.get('product_list')}
        return templates.TemplateResponse(name="menu.html", context=context)


