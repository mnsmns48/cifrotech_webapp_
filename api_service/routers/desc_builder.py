from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.desc_builder.service import DescBuilder
from api_service.schemas import FormulaIdObj, GenerateDescriptionPayload, FetchComposerResponse, SpecsPathRequest, \
    SpecPathResponse, CreateSpecsComposer, SaveSpecsComposer, SpecsComposerResponse, UpdateComposer, CreateSpecPath, \
    UpdateSpecPath, DeleteSpecPath
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


@desc_builder.get('/create_new_composer/{formula_entity_type_id}', response_model=CreateSpecsComposer)
async def create_new_composer(formula_entity_type_id: int,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.create_new_composer(formula_entity_type_id, session)


@desc_builder.post('/save_new_composer', response_model=SpecsComposerResponse)
async def save_new_composer(payload: SaveSpecsComposer, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.save_new_composer(payload, session)


@desc_builder.post('/update_composer', response_model=SpecsComposerResponse)
async def update_composer(payload: UpdateComposer, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.update_composer(payload, session)


@desc_builder.post('/delete_composer/{composer_id}')
async def delete_composer(composer_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.delete_composer(composer_id, session)


@desc_builder.post("/create_spec_path")
async def create_spec_path(payload: CreateSpecPath, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.create_spec_path(payload, session)


@desc_builder.post("/update_spec_path")
async def update_spec_path(payload: UpdateSpecPath, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.update_spec_path(payload, session)


@desc_builder.post("/delete_spec_path")
async def delete_spec_path(payload: DeleteSpecPath, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await DescBuilder.delete_spec_path(payload.id, session)
