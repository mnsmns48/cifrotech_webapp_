from typing import Optional, List, Union, Dict

from pydantic import BaseModel


class HubLevelScheme(BaseModel):
    id: int
    sort_order: int
    label: str
    icon: str | None
    parent_id: int
    depth: int


class HubProductScheme(BaseModel):
    id: int
    origin: int
    warranty: Optional[str]
    output_price: Optional[float]
    title: str
    pics: Optional[List[str]]
    preview: Optional[str]
    model: Optional[str]


class HubProductResponse(BaseModel):
    products: List[HubProductScheme]
    duration_ms: int


class ProductFeaturesSchema(BaseModel):
    id: int
    title: str
    type: str
    brand: str
    source: Optional[str]
    info: Optional[List[Dict]] = None
    pros_cons: Optional[Dict] = None

    model_config = {"from_attributes": True}


class ProductFeaturesResponse(BaseModel):
    features: ProductFeaturesSchema | None


class ServiceImageSchema(BaseModel):
    id: int
    var: str
    value: str

    model_config = {"from_attributes": True}
