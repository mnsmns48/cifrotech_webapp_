from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.service import DescBuilder
from api_service.schemas import FormulaIdObj, GenerateDescriptionPayload
from engine import db

desc_builder = APIRouter(tags=['Desc Builder'], prefix='/desc-builder')


@desc_builder.get('/fetch_formula_link')
async def fetch_formula_link(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.fetch_formula_link(session)


@desc_builder.post('/update_formula_link')
async def update_formula_link(formula: FormulaIdObj, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.update_formula_link(formula, session)


@desc_builder.post('/generate_description')
async def generate_description(payload: GenerateDescriptionPayload,
                               session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.generate_description(payload, session)
