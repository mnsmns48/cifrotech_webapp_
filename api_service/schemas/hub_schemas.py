from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, ConfigDict, HttpUrl

from api_service.schemas.vsl_schemas import VSLScheme
from var_types import PriceDiffStatus


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


class StockInHubItem(BaseModel):
    origin: int
    path_id: int
    warranty: Optional[str]
    input_price: float
    output_price: float

    model_config = {"from_attributes": True}


class HubLoadingData(BaseModel):
    vsl_id: int
    stocks: List[StockInHubItem]

    model_config = {"from_attributes": True}


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


class ComparisonOutScheme(BaseModel):
    vsl_list: list[VSLScheme]
    path_ids: list[HubLevelPath]

    model_config = {"from_attributes": True}


class ParsingLine(BaseModel):
    key: int
    url: HttpUrl
    title: str
    dt_parsed: datetime


class ConsentProcessScheme(BaseModel):
    path_ids: List[int]


class ConsentOutTable(BaseModel):
    origin: int
    path_id: int
    vsl_id: int
    warranty: Optional[str]
    input_price: float
    output_price: Optional[float]
    added_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParsingHubDiffItem(BaseModel):
    origin: int
    title: str
    warranty: Optional[str]
    optional: Optional[str]
    shipment: Optional[str]
    parsing_line_title: str
    parsing_input_price: Optional[float]
    parsing_output_price: Optional[float]
    dt_parsed: datetime
    hub_input_price: float
    hub_output_price: float
    hub_added_at: Optional[datetime]
    hub_updated_at: Optional[datetime]
    status: PriceDiffStatus
    profit_range_id: int

    model_config = {"from_attributes": True}


class ParsingHubDiffOut(BaseModel):
    path_id: int
    label: str
    items: Optional[List[ParsingHubDiffItem]]
