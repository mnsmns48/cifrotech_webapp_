import json
from datetime import datetime
from typing import Union, List, Dict, Any, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import FieldValidationInfo


class ProductOriginBase(BaseModel):
    title: str
    link: Optional[str] = None
    pics: Optional[List[str]] = None
    preview: Optional[str] = None
    is_deleted: bool = False


class ProductOriginCreate(ProductOriginBase):
    origin: int


class ProductOriginRead(ProductOriginBase):
    origin: int

    model_config = {"from_attributes": True}


class ProductOriginUpdate(BaseModel):
    title: str


class ProductDependencyUpdate(BaseModel):
    origin: int
    title: str
    brand: str
    product_type: str
    info: Union[List[Dict[str, Any]], str]
    pros_cons: Optional[Union[Dict[str, List[str]], str]] = Field(default_factory=dict)

    @field_validator("info", "pros_cons", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any, field_info: FieldValidationInfo) -> Any:
        dict_stub = dict()
        if field_info.field_name == "pros_cons" and v is None:
            return dict_stub
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                if field_info.field_name == "pros_cons":
                    return dict_stub
                return v
        return v


class ProductDependencyBatchUpdate(BaseModel):
    items: List[ProductDependencyUpdate]


class ProductResponse(BaseModel):
    title: str
    brand: str
    product_type: str
    info: Dict[str, Dict[str, Any]]
    pros_cons: Optional[dict]
    source: str


class RecalcPricesRequest(BaseModel):
    vsl_id: int
    range_id: int


class RecalcPricesResponse(BaseModel):
    is_ok: bool
    category: list[str]
    datestamp: datetime
    range_reward: int
    data: list


class OriginsList(BaseModel):
    origins: List[int]
