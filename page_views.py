from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud import get_directory, get_products_in_parent
from core.engine import pg_engine

pages_router = APIRouter()
templates = Jinja2Templates(directory="templates")


@pages_router.get("/")
async def get_page(
        request: Request,
        session: AsyncSession = Depends(dependency=pg_engine.scoped_session_dependency),
):
    buttons = await get_directory(session=session, parent=0)
    return templates.TemplateResponse(
        name="products_list.html",
        context={"request": request, "buttons": buttons.get('product_list')}
    )


@pages_router.get("/{parent}")
async def get_page_parent(
        parent: int,
        request: Request,
        session: AsyncSession = Depends(dependency=pg_engine.scoped_session_dependency),
):
    buttons = await get_directory(session=session, parent=parent)
    if buttons.get('destination_folder'):
        return templates.TemplateResponse(
            name="product.html",
            context={"request": request, "buttons": buttons.get('product_list')}
        )
    else:
        return templates.TemplateResponse(
            name="products_list.html",
            context={"request": request, "buttons": buttons.get('product_list')}
        )


@pages_router.get("/s/{parent}")
async def get_products_in_parent_(
        parent: int,
        request: Request,
        session: AsyncSession = Depends(dependency=pg_engine.scoped_session_dependency),
):
    buttons = await get_products_in_parent(session=session, parent=parent)
    return templates.TemplateResponse(
        name="product.html",
        context={"request": request, "buttons": buttons}
    )
