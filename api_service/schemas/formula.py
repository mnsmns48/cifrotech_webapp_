from pydantic import BaseModel
from typing import Optional, Dict, Any


class FormulaBase(BaseModel):
    name: Optional[str] = None
    formula: Optional[str] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


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
    entity_type: Optional[str]
    is_active: bool
    is_default: bool

    class Config:
        from_attributes = True


class FormulaPreviewRequest(BaseModel):
    context: Dict[str, Any]


class FormulaPreviewResponse(BaseModel):
    result: str


class FormulaValidateRequest(BaseModel):
    formula: str
