from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_v2.crud import get_menu, get_recursive_menu
from engine import pg_engine

api_v2_router = APIRouter(prefix="/api2")


# @api_v2_router.get("/")
# async def get_root(session_pg: AsyncSession = Depends(pg_engine.scoped_session_dependency)):
#     menu_data = await get_menu(session_pg)
#     return {"menu": menu_data}

@api_v2_router.get("/")
async def get_root(session_pg: AsyncSession = Depends(pg_engine.scoped_session_dependency)):
    menu_data = await get_recursive_menu(session_pg)
    return {"menu": menu_data}
