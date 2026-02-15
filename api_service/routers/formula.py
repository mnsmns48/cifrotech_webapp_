from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud_attributes import fetch_all_attribute_keys
from api_service.formula.environment import validate_formula, env
from api_service.formula.filters import FILTER_DOCS
from api_service.formula.service import FormulaService
from api_service.schemas import (
    FormulaResponse,
    FormulaCreate,
    FormulaUpdate,
    FormulaPreviewResponse,
    FormulaPreviewRequest,
    FormulaValidateRequest,
)
from engine import db

formula_router = APIRouter(prefix="/formula-expression", tags=["Formula Expression"])


@formula_router.get("/default", response_model=FormulaResponse)
async def get_default_formula(entity_type: str | None = None,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    formula = await FormulaService.get_default(session, entity_type)
    if not formula:
        raise HTTPException(404, "Default formula not found")
    return formula


@formula_router.get("/filter-docs")
async def get_filter_docs():
    return FILTER_DOCS


@formula_router.get("/context-schema")
async def get_context_schema(session: AsyncSession = Depends(db.scoped_session_dependency)):
    attr_keys = await fetch_all_attribute_keys(session)

    attributes_schema = {
        key.key: "dict(value: string, alias: string | null)"
        for key in attr_keys
    }

    return {
        "model": "string",
        "attributes": attributes_schema
    }


@formula_router.get("/", response_model=list[FormulaResponse])
async def get_all_formulas(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await FormulaService.get_all(session)


@formula_router.get("/{formula_id}", response_model=FormulaResponse)
async def get_formula(formula_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    formula = await FormulaService.get_by_id(session, formula_id)
    if not formula:
        raise HTTPException(404, "Formula not found")
    return formula


@formula_router.post("/", response_model=FormulaResponse)
async def create_formula(data: FormulaCreate, session: AsyncSession = Depends(db.scoped_session_dependency)):
    formula = await FormulaService.create(session, data)
    return formula


@formula_router.put("/{formula_id}", response_model=FormulaResponse)
async def update_formula(
        formula_id: int,
        data: FormulaUpdate,
        session: AsyncSession = Depends(db.scoped_session_dependency)
):
    formula = await FormulaService.update(session, formula_id, data)
    if not formula:
        raise HTTPException(404, "Formula not found")
    return formula


@formula_router.delete("/{formula_id}")
async def deactivate_formula(formula_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    formula = await FormulaService.deactivate(session, formula_id)
    if not formula:
        raise HTTPException(404, "Formula not found")
    return {"status": "ok"}


@formula_router.post("/{formula_id}/preview", response_model=FormulaPreviewResponse)
async def preview_formula(
        formula_id: int, body: FormulaPreviewRequest, session: AsyncSession = Depends(db.scoped_session_dependency)):
    formula = await FormulaService.get_by_id(session, formula_id)
    if not formula:
        raise HTTPException(404, "Formula not found")

    result = await FormulaService.preview(formula.formula, body.context)
    return FormulaPreviewResponse(result=result)


@formula_router.post("/validate")
async def validate_formula_api(body: FormulaValidateRequest):
    errors = validate_formula(body.formula)
    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}


@formula_router.get("/filters")
async def get_filters():
    return {"filters": list(env.filters.keys())}


@formula_router.post("/is_default")
async def formula_is_default(formula_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    await FormulaService.set_default(session, formula_id)
    return {"status": True}
