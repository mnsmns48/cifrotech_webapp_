from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any


class FormulaBase(BaseModel):
    name: Optional[str] = None
    formula: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[int] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class FormulaEntityTypeScheme(BaseModel):
    id: int
    title_type: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CreateFormulaEntityType(BaseModel):
    title_type: str
    description: Optional[str] = None


class FormulaCreate(FormulaBase):
    name: str
    formula: str


class FormulaUpdate(FormulaBase):
    pass


class FormulaResponse(BaseModel):
    id: int
    name: str
    formula: str
    description: Optional[str]
    entity_type: Optional[FormulaEntityTypeScheme]
    is_active: bool
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


class FormulaPreviewRequest(BaseModel):
    context: Dict[str, Any]


class FormulaPreviewResponse(BaseModel):
    result: str


class FormulaValidateRequest(BaseModel):
    formula: str


class FormulaIdObj(BaseModel):
    id: int
    name: str
