from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_no_img_pic
from app_utils import get_url_from_s3
from config import settings
from engine import db

service_mini_app = APIRouter()


@service_mini_app.get('/get_no_img_pic')
@cache(expire=3600)
async def get_no_img_pic(session: AsyncSession = Depends(db.scoped_session_dependency),
                         var: str = 'no_img'):
    response = await fetch_no_img_pic(session, var)
    if response is None:
        return None
    return get_url_from_s3(filename=response.value, path=settings.s3.utils_path)
