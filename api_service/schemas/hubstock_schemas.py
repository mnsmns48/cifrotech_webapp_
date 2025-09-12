from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class StockInHubItem(BaseModel):
    origin: int
    path_id: int
    warranty: Optional[str]
    input_price: float
    output_price: float
    profit_range_id: Optional[int]

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
    profit_range_id: Optional[int]


class HubItemChangeScheme(BaseModel):
    origin: int
    title: str
    new_price: float


class OriginsPayload(BaseModel):
    origins: list[int]
