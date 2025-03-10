import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from api_v2.crud2 import get_root_menu, get_page_items
from cfg import settings
from engine import pg_engine

api_v2_router = APIRouter(prefix="/api2")


@api_v2_router.get("/")
async def get_root(session_pg: AsyncSession = Depends(pg_engine.scoped_session_dependency)):
    menu_data = await get_root_menu(session_pg)
    return {"root_menu": menu_data}


@api_v2_router.get("/{items_key}")
async def get_items(items_key: int, session_pg: AsyncSession = Depends(pg_engine.scoped_session_dependency)):
    items = await get_page_items(items_key=items_key, session_pg=session_pg)
    return {'items': items}


@api_v2_router.get("/images/{image_name}")
async def get_image(image_name: str):
    image_path = os.path.join(settings.photo_path, image_name)
    if os.path.exists(image_path):
        return FileResponse(image_path)
    return {"error": "Image not found"}
