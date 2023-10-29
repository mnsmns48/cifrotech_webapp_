from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud import get_directory
from core.engine import pg_engine
from core.schemas import Dir


pages_router = APIRouter()
static = Jinja2Templates(directory="static")


@pages_router.get("/{parent}", response_model=list[Dir])
async def get_page(
    parent: int,
    request: Request,
    session: AsyncSession = Depends(dependency=pg_engine.scoped_session_dependency),
):
    buttons = await get_directory(session=session, parent=parent)
    return static.TemplateResponse(
        "index.html", {"request": request, "buttons": buttons}
    )


# @router.get("/")
# async def get_main(request: Request, session: AsyncSession = Depends(pg_engine.session_dependency)):
#     response = await get_directory(session=session, parent=0)
#     print(response)
#     return templates.TemplateResponse("index.html", {"request": request})
