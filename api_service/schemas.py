from fastapi import Form


async def take_form_result(
        receipt_date: str = Form(...),
        receipt_number: int = Form(...),
        receipt_product: str = Form(...),
        receipt_qty: int = Form(...),
        receipt_price: float = Form(...)):
    return {"receipt_date": receipt_date,
            "receipt_number": receipt_number,
            "receipt_product": receipt_product,
            "receipt_qty": receipt_qty,
            "receipt_price": receipt_price}
