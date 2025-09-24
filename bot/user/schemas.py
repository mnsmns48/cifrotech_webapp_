from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class HubMenuLevel(BaseModel):
    id: int
    label: str
    icon: Optional[str] = None
    sort_order: int

    model_config = {"from_attributes": True}


class HubStockItem(BaseModel):
    title: str
    price: float
    origin: int


class HubStockResponse(BaseModel):
    items: List[HubStockItem]
    most_common_updated_at: Optional[str]
