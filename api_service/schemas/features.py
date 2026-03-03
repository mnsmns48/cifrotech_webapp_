from typing import List, Optional, Dict, Literal

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
