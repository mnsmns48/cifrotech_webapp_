from typing import Optional, List, Union

from pydantic import BaseModel


class HubLevelScheme(BaseModel):
    id: int
    sort_order: int
    label: str
    icon: str | None
    parent_id: int
    depth: int


class HubProductScheme(BaseModel):
    id: int
    origin: int
    warranty: Optional[str]
    output_price: Optional[float]
    title: str
    pics: Optional[List[str]]
    preview: Optional[str]
    model: Optional[str]


class HubProductResponse(BaseModel):
    products: List[HubProductScheme]
    duration_ms: int
