from typing import Any

from pydantic import BaseModel

from api_service.schemas import BrandModel, TypeModel, FormulaResponse


class GenerateDescriptionPayload(BaseModel):
    product_features_map: dict[int, dict | None]


class SpecsParamScheme(BaseModel):
    category: str
    param: str


class SpecsComposerExpandedScheme(BaseModel):
    id: int
    type: TypeModel
    brand: BrandModel | None
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
