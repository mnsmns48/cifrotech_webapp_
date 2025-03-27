from fastapi import Form
from pydantic import BaseModel


async def take_form_result(
    receipt_date: str = Form(...),
    receipt_product: str = Form(...),
    receipt_qty: int = Form(...),
    receipt_price: float = Form(...)
):
    return {
        "receipt_date": receipt_date,
        "receipt_product": receipt_product,
        "receipt_qty": receipt_qty,
        "receipt_price": receipt_price,
    }
