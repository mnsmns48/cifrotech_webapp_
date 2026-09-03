from datetime import datetime
from typing import Optional, List, Dict

from pydantic import BaseModel, Field

from api_miniapp.schemas import HubProductScheme
from api_service.schemas import AttributeKeyValueSchema, HubLevelPath, TypeModel, BrandModel, HubMenuLevelSchema
from api_service.schemas.desc_builder import BlockResponse
from api_service.schemas.features_schemas import FeatureProductScheme


class HubLevelSchemeV3(HubMenuLevelSchema):
    slug: str
    depth: int


class HubProductSchemeExtV3(HubProductScheme):
    short_specs: list[BlockResponse] | None = None


class HubProductSchemeExtV3Attrs(HubProductSchemeExtV3):
    attrs: list[str] | None = None


class InfiniteProductsResponse(BaseModel):
    products: list[HubProductSchemeExtV3]
    next_cursor: int | None = None
    has_more: bool
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
    short_specs: list[BlockResponse] | None = None
    full_specs: Optional[FeatureProductScheme] = None
    duration: int


class CategoryQuery(BaseModel):
    path: str = Field(..., description="Path like 'smartfony/apple/iphone'")
    page: int = Field(1, ge=1)
    limit: int = Field(24, ge=1, le=200)
    sort: Optional[str] = None


class Pagination(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class FilterOption(BaseModel):
    key: str
    label: str
    type: str
    values: list
    active: list
    meta: Optional[dict]


class SortOption(BaseModel):
    key: str
    label: str


class SortResponse(BaseModel):
    active: Optional[str]
    options: list[SortOption]


class FiltersResponse(BaseModel):
    sku_filters: list[FilterOption]
    model_filters: list[FilterOption]


class CategoryProductsResponse(BaseModel):
    breadcrumbs: list[HubLevelSchemeV3]
    filters: FiltersResponse
    products: list[HubProductSchemeExtV3]
    pagination: Pagination
    sort: SortResponse
    filters_hash: str
    duration_ms: int


class CategoryItem(BaseModel):
    hubstock_id: int
    origin: int
    warranty: Optional[str]
    output_price: Optional[float]
    title: str
    model: Optional[str]
    feature_id: Optional[int]
    type: Optional[TypeModel]
    brand: Optional[BrandModel]
    pics: list[str] = []
    preview: Optional[str] = None
    updated_at: datetime
    attr_values: dict[str, list[int]] = {}
