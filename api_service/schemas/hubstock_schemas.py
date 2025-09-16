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
    dt_parsed: Optional[datetime]
    features_title: list
    profit_range: Optional[RewardRangeBaseSchema]


class OriginsPayload(BaseModel):
    origins: list[int]


class HubItemTitlePatch(BaseModel):
    origin: int
    new_title: str


class PriceChange(BaseModel):
    origin: int
    new_price: Optional[float] = None


class HubItemsChangePriceRequest(BaseModel):
    price_update: list[PriceChange]
    new_profit_range_id: Optional[int] = None


class HubItemsChangePriceResponse(BaseModel):
    origin: int
    new_price: float
    updated_at: datetime
    profit_range: Optional[RewardRangeBaseSchema]
