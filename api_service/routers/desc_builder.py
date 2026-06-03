from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.service import DescBuilder
from api_service.schemas import FormulaIdObj, GenerateDescriptionPayload, FetchComposerResponse, SpecsPathRequest, \
    SpecPathResponse
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


@desc_builder.get('/fetch_composer/{formula_entity_type_id}', response_model=FetchComposerResponse)
async def fetch_composer(formula_entity_type_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.fetch_composer(formula_entity_type_id, session)


@desc_builder.post('/fetch_spec_path', response_model=List[SpecPathResponse])
async def fetch_spec_path(payload: SpecsPathRequest, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.fetch_spec_path(payload, session)
