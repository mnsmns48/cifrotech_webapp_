from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.service import DescBuilder
from engine import db

desc_builder = APIRouter(tags=['Desc Builder'], prefix='/desc-builder')


@desc_builder.get('/fetch_formula_link')
async def fetch_formula_link(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.fetch_formula_link(session)
