from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, HttpUrl


class HubMenuLevelSchema(BaseModel):
    id: int
    sort_order: int
    label: str
    icon: Optional[str]
    parent_id: int

    class Config:
        from_attributes = True


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


class StockInHubItem(BaseModel):
    origin: int
    path_id: str
    vsl_id: str
    warranty: float
    input_price: float
    output_price: float
    added_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HubLoadingData(BaseModel):
    vsl_id: int
    stocks: List[StockInHubItem]

    class Config:
        from_attributes = True


class HubItemChangeScheme(BaseModel):
    origin: int
    title: str
    new_price: float


class OriginsPayload(BaseModel):
    origins: list[int]


class ComparisonDataScheme(BaseModel):
    origins: Optional[list[int]] = None
    path_id: int


class ParsingLine(BaseModel):
    key: int
    url: HttpUrl
    title: str
    dt_parsed: datetime
