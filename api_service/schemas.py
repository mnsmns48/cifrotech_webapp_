import logging
from typing import List, Optional, Dict, Union

from fastapi import Form
from pydantic import BaseModel, Field, confloat, conint
from pydantic_core.core_schema import FieldValidationInfo


class ReceiptForm(BaseModel):
    receipt_date: str = Field(...)
    receipt_number: int = Field(...)
    receipt_product: str = Field(...)
    receipt_qty: int = Field(...)
    receipt_price: float = Field(...)

    @property
    def total(self) -> float:
        return self.receipt_qty * self.receipt_price


def get_receipt_form(
        receipt_date: str = Form(...),
        receipt_number: int = Form(...),
        receipt_product: str = Form(...),
        receipt_qty: int = Form(...),
        receipt_price: float = Form(...)
) -> ReceiptForm:
    return ReceiptForm(receipt_date=receipt_date,
                       receipt_number=receipt_number,
                       receipt_product=receipt_product,
                       receipt_qty=receipt_qty,
                       receipt_price=receipt_price)


class VendorSchema(BaseModel):
    id: int
    name: str
    source: str | None = None
    telegram_id: str | None = None
    login: str | None = None
    password: str | None = None
    function: str | None = None

    @classmethod
    def cls_validate(cls, vendor, exclude_id=False):
        if exclude_id:
            return cls.model_validate(vendor.__dict__).model_dump(exclude={"id"})
        return cls.model_validate(vendor.__dict__).model_dump()


class VendorSearchLineSchema(BaseModel):
    id: int
    vendor_id: int
    title: str
    url: str

    @classmethod
    def cls_validate(cls, vendor, exclude_id=False):
        if exclude_id:
            return cls.model_validate(vendor.__dict__).model_dump(exclude={"id"})
        return cls.model_validate(vendor.__dict__).model_dump()


class ParsingRequest(BaseModel):
    progress: str
    vsl_id: int
    vsl_url: str


class RewardRangeLineSchema(BaseModel):
    range_id: int
    line_from: int
    line_to: int
    is_percent: bool
    reward: int

    class Config:
        from_attributes = True


class RewardRangeSchema(BaseModel):
    title: str


class HarvestLineIn(BaseModel):
    origin: conint(ge=0)
    title: str
    link: Optional[str] = None
    shipment: Optional[str] = None
    warranty: Optional[str] = None
    input_price: Optional[confloat(ge=0)] = None
    output_price: Optional[confloat(ge=0)] = None
    pics: Optional[List[str]] = None
    preview: Optional[str] = None
    optional: Optional[str] = None
    harvest_id: conint(ge=1)

    model_config = {"from_attributes": True, "extra": "ignore"}


class ProductOriginUpdate(BaseModel):
    title: str


from typing import Any
from pydantic import BaseModel, field_validator
import json


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


class ProductResponse(BaseModel):
    title: str
    brand: str
    product_type: str
    info: Dict[str, Dict[str, Any]]
    pros_cons: Optional[dict]
    source: str
