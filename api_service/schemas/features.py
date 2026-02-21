from typing import List, Optional

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
