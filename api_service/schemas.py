import logging
from typing import List

from fastapi import Form
from pydantic import BaseModel, Field

logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)


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
    url: str


class RewardRangeLineSchema(BaseModel):
    id: int
    range_id: int
    line_from: int
    line_to: int
    is_percent: bool
    reward: int

    @classmethod
    def cls_validate(cls, data, exclude_id=False):
        if exclude_id:
            return cls.model_validate(data.__dict__).model_dump(exclude={"id"})
        return cls.model_validate(data.__dict__).model_dump()

    class Config:
        from_attributes = True


class RewardRangeSchema(BaseModel):
    title: str
