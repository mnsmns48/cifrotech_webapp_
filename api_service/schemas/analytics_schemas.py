from pydantic import BaseModel, ConfigDict

from api_service.schemas.product_schemas import TypeModel
from api_service.schemas.attribute_schemas import AttributeKey, AttributeValueSchema


class ProductTypeValueMapSchema(BaseModel):
    id: int
    attr_value: AttributeValueSchema
    multiplier: float


class ProductTypeWeightRuleSchema(BaseModel):
    id: int
    product_type: TypeModel
    attr_key: AttributeKey
    weight: float
    value_maps: list[ProductTypeValueMapSchema] | None = None
    description: str | None = None
    is_enabled: bool

    model_config = ConfigDict(from_attributes=True)


class ProductTypeWeightRuleCreate(BaseModel):
    product_type_id: int
    attr_key_id: int
    weight: float
    description: str | None = None
    is_enabled: bool = True


class ProductTypeWeightRuleDelete(BaseModel):
    id: int


class ProductTypeWeightRuleUpdate(BaseModel):
    id: int
    product_type_id: int
    attr_key_id: int
    weight: float
    description: str | None = None
    is_enabled: bool = True


class ProductTypeWeightRuleSwitch(BaseModel):
    id: int
    is_enabled: bool


class ProductTypeValueMapScheme(BaseModel):
    id: int
    attr_value: AttributeValueSchema
    multiplier: float


class ProductTypeValueMapCreateSchema(BaseModel):
    rule_id: int
    attr_value_ids: list[int]
    multiplier: float


class ProductTypeValueMapUpdateSchema(BaseModel):
    id: int | list[int]
    multiplier: float


class ProductTypeValueMapDeleteSchema(BaseModel):
    ids: list[int]


class AnalyzeItem(BaseModel):
    verdict: bool
    ratio: float
    threshold: float
    price_increase: float
    value_increase: float
    value: float
