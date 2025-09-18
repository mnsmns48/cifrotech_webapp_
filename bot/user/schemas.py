from typing import Optional

from pydantic import BaseModel


class HubMenuLevel(BaseModel):
    id: int
    label: str
    icon: Optional[str] = None
    sort_order: int

    model_config = {"from_attributes": True}
