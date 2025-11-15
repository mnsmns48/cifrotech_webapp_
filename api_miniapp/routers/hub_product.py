from typing import List

from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
from api_miniapp.schemas import HubLevelScheme
from engine import db

hub_product = APIRouter()


@hub_product.get("/hub_levels", response_model=List[HubLevelScheme])
@cache(expire=10)
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)
