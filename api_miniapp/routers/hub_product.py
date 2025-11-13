from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
from engine import db

hub_product = APIRouter()


@hub_product.get("/hub_levels")
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)
