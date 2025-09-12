from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, HttpUrl

from api_service.schemas.vsl_schemas import VSLScheme
from api_service.schemas.hub_schemas import HubLevelPath
from var_types import PriceDiffStatus


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


class RecomputedNewPriceLines(BaseModel):
    origin: int
    title: str
    old_price: float
    new_price: float
