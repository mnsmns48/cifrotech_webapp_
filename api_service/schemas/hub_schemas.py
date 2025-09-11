from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, HttpUrl

from api_service.schemas.range_reward_schemas import RewardRangeResponseSchema
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


class ParsingHubDiffItem(BaseModel):
    origin: int
    title: str

    warranty: Optional[str] = None
    optional: Optional[str] = None
    shipment: Optional[str] = None
    url: Optional[str] = None
    parsing_line_title: Optional[str] = None
    parsing_input_price: Optional[float] = None
    parsing_output_price: Optional[float] = None
    dt_parsed: Optional[datetime] = None
    hub_input_price: Optional[float] = None
    hub_output_price: Optional[float] = None
    hub_added_at: Optional[datetime] = None
    hub_updated_at: Optional[datetime] = None

    status: PriceDiffStatus

    model_config = {"from_attributes": True}

    @property
    def sort_price(self) -> float:
        if self.parsing_input_price is not None:
            return self.parsing_input_price
        return self.hub_input_price or 0.0


class ParsingHubDiffOut(BaseModel):
    path_id: int
    label: str
    items: Optional[List[ParsingHubDiffItem]]


class HubToDiffData(BaseModel):
    origin: int
    title: str
    url: Optional[str]
    vsl_id: int
    warranty: Optional[str]
    hub_input_price: float
    hub_output_price: Optional[float]
    hub_added_at: datetime
    hub_updated_at: datetime

    model_config = {"from_attributes": True}


class RecalcScheme(BaseModel):
    path_ids: List[int]
    origins: Optional[List[int]]
    rr_profile: Optional[RewardRangeResponseSchema]
