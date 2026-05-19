from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, HttpUrl, model_validator

from api_service.schemas.range_reward_schemas import RewardRangeBaseSchema
from api_service.schemas.vsl_schemas import VSLScheme
from api_service.schemas.hub_schemas import HubMenuLevelSchema
from api_service.schemas.product_schemas import TypeModel, BrandModel, ModelForApprove
from api_service.schemas.attribute_schemas import AttributeValueSchema
from var_types import PriceDiffStatus


class PathIdRequest(BaseModel):
    path_id: int


class HubRoutes(BaseModel):
    path_id: int
    route: List[HubMenuLevelSchema]


class PriceSyncPickedPath(HubRoutes):
    vsl_list: list[VSLScheme]

    model_config = {"from_attributes": True}


class RawOrigin(BaseModel):
    type_: Optional[TypeModel]
    brand: Optional[BrandModel]
    origin: int
    title: str
    vsl_id: int
    price: Optional[float]
    model_id: Optional[int]
    model_title: Optional[str]
    have_attributes: Optional[list[AttributeValueSchema]]
    have_images: bool
    model_in_hub: bool


class SyncPathWOrigins(PriceSyncPickedPath):
    raw_origin_ids: list[RawOrigin]


class SyncPathWModels(HubRoutes):
    path_id: int
    route: List[HubMenuLevelSchema]
    models: List[ModelForApprove]


class ParsingLine(BaseModel):
    key: int
    url: HttpUrl
    title: str
    dt_parsed: datetime


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


class RecomputedNewPriceLines(BaseModel):
    origin: int
    title: str
    input_parsing_price: float
    output_parsing_price: float
    output_stock_price: float


class RecomputedResult(BaseModel):
    path_id: int
    label: str
    recomputed_items: Optional[List[RecomputedNewPriceLines]]


class UpdateHubApproveItem(BaseModel):
    path_id: int
    models_ids: list[int]


class UpdateHubApproveItems(BaseModel):
    items: List[UpdateHubApproveItem]


class ProductMarketSettingsSchema(BaseModel):
    id: int
    path_id: int
    market_variance_scale: float = 5.0
    market_variance_exponent: float = 1.1

    model_config = {
        "from_attributes": True
    }


class SyncPathWMarket(SyncPathWModels):
    market: ProductMarketSettingsSchema


class UpdateMarketSettingsRequest(SyncPathWModels):
    market_variance_scale: float | None = None
    market_variance_exponent: float | None = None

    @model_validator(mode="after")
    def validate_at_least_one(self):
        if (
                self.market_variance_scale is None and
                self.market_variance_exponent is None
        ):
            raise ValueError(
                "Нужно передать хотя бы одно из полей: "
                "market_variance_scale или market_variance_exponent"
            )
        return self


class HubPayloadPriceSyncItem(BaseModel):
    origin: int
    title: str
    vsl_id: int
    warranty: Optional[str]
    input_price: float
    output_price: float
    dt_parsed: datetime
    model_title: str
    profit_range: Optional[RewardRangeBaseSchema]

    model_config = {"from_attributes": True}


class HubStockUpdateSyncPathItem(BaseModel):
    path_id: int
    hub_item: HubPayloadPriceSyncItem
