from typing import Optional, List

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
