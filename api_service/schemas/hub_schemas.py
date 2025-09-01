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
    path_id: int
    warranty: Optional[str]
    input_price: float
    output_price: float

    class Config:
        from_attributes = True


class HubLoadingData(BaseModel):
    vsl_id: int
    stocks: List[StockInHubItem]

    class Config:
        from_attributes = True


class StockHubItemResult(BaseModel):
    origin: int
    title: str
    warranty: Optional[str]
    input_price: float
    output_price: float
    updated_at: datetime
    dt_parsed: datetime
    features_title: list


class HubItemChangeScheme(BaseModel):
    origin: int
    title: str
    new_price: float


class OriginsPayload(BaseModel):
    origins: list[int]


class ComparisonInScheme(BaseModel):
    origins: Optional[list[int]] = None
    path_id: int


# class ComparisonOut(BaseModel):


class ParsingLine(BaseModel):
    key: int
    url: HttpUrl
    title: str
    dt_parsed: datetime


class ConsentProcessScheme(BaseModel):
    path_ids: List[int]
