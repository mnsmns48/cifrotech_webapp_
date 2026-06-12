from typing import Any, Optional, Dict, List

from pydantic import BaseModel, ConfigDict, Field, model_validator

from api_service.schemas import TypeModel, FormulaResponse


class GenerateDescriptionPayload(BaseModel):
    product_features_map: dict[int, dict | None] | None = None
    origins: list[int] | None = None


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
    id: int
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


class UpdateComposer(SpecsComposerResponse):
    pass


class CreateSpecPath(BaseModel):
    title: str = Field(..., max_length=100)
    path: List[Any]
    formula_id: int
    source: str


class UpdateSpecPath(BaseModel):
    id: int
    title: str = Field(..., max_length=100)
    path: List[Any]


class DeleteSpecPath(BaseModel):
    id: int


class BlockResponse(BaseModel):
    title: Optional[str] = None
    icon: Optional[str] = None
    text: str
    values: Dict[str, str]


class ProductDescription(BaseModel):
    blocks: List[BlockResponse] = Field(default_factory=list)


class DescriptionSuccess(BaseModel):
    products: Dict[int, ProductDescription]


class DescriptionError(BaseModel):
    error: str
    details: Optional[str] = None


class DescriptionResponse(BaseModel):
    success: Optional[DescriptionSuccess] = None
    error: Optional[DescriptionError] = None
