import logging
from typing import Optional

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
    progress: Optional[str] = None
    vendor_id: int
    title: str
    url: str

    class Config:
        from_attributes = True
