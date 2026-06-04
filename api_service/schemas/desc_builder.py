from typing import Any

from pydantic import BaseModel, ConfigDict

from api_service.schemas import TypeModel, FormulaResponse


class GenerateDescriptionPayload(BaseModel):
    product_features_map: dict[int, dict | None]


class SpecsParamScheme(BaseModel):
    category: str
    param: str


class SpecsComposerExpandedScheme(BaseModel):
    id: int
    type: TypeModel
    source: str
    formula: FormulaResponse


class FetchComposerResponse(BaseModel):
    entity_type_id: int
    composers: list[SpecsComposerExpandedScheme]


class SpecsPathRequest(BaseModel):
    formula_id: int
    source: str


class SpecPathResponse(BaseModel):
    title: str
    path: list[Any]
    icon: str | None = None


class CreateSpecsComposer(BaseModel):
    types: list[TypeModel]
    sources: list[str]
    formulas: list[FormulaResponse]


class SaveSpecsComposer(BaseModel):
    type_id: int
    source: str
    formula_id: int


class SpecsComposerResponse(SaveSpecsComposer):
    id: int

    model_config = ConfigDict(from_attributes=True)
