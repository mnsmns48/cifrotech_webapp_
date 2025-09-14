from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from api_service.schemas.range_reward_schemas import RewardRangeBaseSchema


class StockInHubItem(BaseModel):
    origin: int
    path_id: int
    warranty: Optional[str]
    input_price: float
    output_price: float
    profit_range: Optional[RewardRangeBaseSchema]

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
    profit_range: Optional[RewardRangeBaseSchema]


class PriceChange(BaseModel):
    origin: int
    new_price: float


class HubItemChangeRequest(BaseModel):
    title_updates: Optional[dict[int, str]] = None
    price_updates: Optional[list[PriceChange]] = None
    new_profit_range_id: Optional[int] = None


class OriginsPayload(BaseModel):
    origins: list[int]


class ProfitRangeOut(BaseModel):
    id: int
    title: str


class HubItemChangeResponse(BaseModel):
    origin: int
    new_title: str
    new_price: float
    updated_at: Optional[datetime]
    profit_range: Optional[ProfitRangeOut]
