from pydantic import BaseModel


class HubLevelScheme(BaseModel):
    id: int
    sort_order: int
    label: str
    icon: str | None
    parent_id: int
    depth: int
