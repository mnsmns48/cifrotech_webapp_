from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.service import DescBuilder
from api_service.schemas import DescriptionResponse, GenerateDescriptionPayload
from engine import db

description_router = APIRouter()


@description_router.post('/generate_description', response_model=DescriptionResponse)
async def generate_description(payload: GenerateDescriptionPayload,
                               session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.generate_description(payload, session)