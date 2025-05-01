import logging

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