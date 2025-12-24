from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud_attributes import fetch_all_attribute_keys
from engine import db

attributes_router = APIRouter(tags=['Attributes'])


@attributes_router.get("/get_attr_keys")
async def get_hub_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_all_attribute_keys(session)
