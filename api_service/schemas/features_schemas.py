from typing import List, Optional, Dict, Literal

from pydantic import BaseModel

from api_service.schemas import HubLevelPath, FormulaIdObj, BrandModel, TypeModel


class FeaturesElement(BaseModel):
    id: int
    brand: BrandModel
    type: TypeModel
    source: str
    title: str
    hub_level: Optional[HubLevelPath]
    formula: Optional[FormulaIdObj]


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
    pros_cons: dict | None = None


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


class TypesAndBrands(BaseModel):
    types: List[TypeModel]
    brands: List[BrandModel]


class CreateFeaturesGlobal(BaseModel):
    title: str
    type_obj: TypeModel
    brand_obj: BrandModel


class SetFeaturesFormulaRequest(BaseModel):
    feature_ids: List[int]
    formula_id: int
    formula_name: str


class SetFormulaResponse(BaseModel):
    updated: Dict[int, FormulaIdObj]


class InsertedBlock(BaseModel):
    param: str
    bulk: str


class InsertBulkParams(BaseModel):
    feature_id: int
    bulk: List[InsertedBlock]


class FeatureBulkResponseScheme(BaseModel):
    id: int
    title: str
    info: list
    pros_cons: dict | None = None
