from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SaleItemScheme(BaseModel):
    time_: datetime
    product: str
    quantity: int
    sum_: float
    noncash: bool
    return_: bool
    remain: Optional[int] = None
