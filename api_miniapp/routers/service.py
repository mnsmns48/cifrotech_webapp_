from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_no_img_pic
from app_utils import get_url_from_s3
from config import settings
from engine import db

service_mini_app = APIRouter()


@service_mini_app.get('/get_no_img_pic')
# @cache(expire=3600)
async def get_no_img_pic(session: AsyncSession = Depends(db.scoped_session_dependency)):
    response = await fetch_no_img_pic(session)
    if response is None:
        return None
    result = {
        item.var: get_url_from_s3(item.value, settings.s3.utils_path)
        for item in response
    }
    return result
