from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.features import features_hub_level_link_fetch_db
from api_service.schemas.features import FeaturesDataSet
from engine import db

features_router = APIRouter(tags=['Features'])


@features_router.get("/features/features_hub_level_link_fetch", response_model=FeaturesDataSet)
async def features_hub_level_link_fetch(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await features_hub_level_link_fetch_db(session)
