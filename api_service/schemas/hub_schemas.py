from typing import Optional

from pydantic import BaseModel


class HubMenuLevelSchema(BaseModel):
    id: int
    sort_order: int
    label: str
    icon: Optional[str]
    parent_id: int

    model_config = {"from_attributes": True}


class HubLevelPath(BaseModel):
    path_id: int
    label: str


class RenameRequest(BaseModel):
    id: int
    new_label: str


class HubPositionPatch(BaseModel):
    id: int
    parent_id: int
    after_id: Optional[int] = None


class HubPositionPatchOut(BaseModel):
    status: bool
    id: int
    parent_id: int
    sort_order: int


class AddHubLevelScheme(BaseModel):
    parent_id: int
    label: str


class AddHubLevelOutScheme(BaseModel):
    status: bool
    id: int
    label: str
    parent_id: int
    sort_order: int
