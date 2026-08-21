from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel

from api_miniapp.schemas import HubProductScheme
from api_service.schemas import AttributeKeyValueSchema, HubLevelPath, TypeModel, BrandModel, HubMenuLevelSchema
from api_service.schemas.desc_builder import BlockResponse
from api_service.schemas.features_schemas import FeatureProductScheme


class HubLevelSchemeV3(HubMenuLevelSchema):
    slug: str
    depth: int


class HubProductSchemeExtV3(HubProductScheme):
    attrs: list[AttributeKeyValueSchema]
    short_specs: list[BlockResponse] | None = None


class BatchProductsResponse(BaseModel):
    products: list[HubProductSchemeExtV3]
    next_cursor: int | None = None
    has_more: bool
    filters_hash: str
    duration_ms: int


class ProductV3Response(BaseModel):
    id: int
    origin: int
    route: list[HubLevelPath]
    warranty: Optional[str] = None
    output_price: Optional[float] = None
    title: str
    updated_at: datetime
    type_obj: Optional[TypeModel] = None
    brand_obj: Optional[BrandModel] = None
    attrs: List[AttributeKeyValueSchema] = []
    pics: List[str] = []
    preview: Optional[str] = None
    pros_cons: Optional[Dict] = None
    full_specs: Optional[FeatureProductScheme] = None
    duration: int
