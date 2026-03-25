from typing import List, Optional, Dict, Literal, Tuple

from pydantic import BaseModel

from api_service.schemas import HubLevelPath
from api_service.schemas.product_schemas import BrandModel, TypeModel


class FeaturesElement(BaseModel):
    id: int
    brand: BrandModel
    type: TypeModel
    title: str
    hub_level: Optional[HubLevelPath]


class FeaturesDataSet(BaseModel):
    features: List[FeaturesElement]


class SetFeaturesHubLevelRequest(BaseModel):
    feature_ids: List[int]
    hub_level_id: int
    label: str


class SetLevelRoutesResponse(BaseModel):
    updated: Dict[int, HubLevelPath]


class FeatureResponseScheme(BaseModel):
    id: int
    title: str
    info: List[Dict]
    pros_cons: dict


class ProsConsItem(BaseModel):
    id: int
    attribute: Literal["advantage", "disadvantage"]
    value: str


class ProsConsItemUpdate(BaseModel):
    id: int
    attribute: Literal["advantage", "disadvantage"]
    old_value: str
    new_value: str


class FeatureCategory(BaseModel):
    id: int
    category_title: str


class UpdateFeatureCategoryRequest(BaseModel):
    id: int
    old_category_title: str
    new_category_title: str


class InnerRowRequest(BaseModel):
    id: int
    category_title: str
    new_param: str
    new_value: str


class UpdateInnerRowRequest(BaseModel):
    id: int
    category_title: str
    old_param: str
    old_value: str
    new_param: str
    new_value: str


class FeatureIds(BaseModel):
    feature_ids: List[int]
