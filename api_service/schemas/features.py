from typing import List, Optional, Dict

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
