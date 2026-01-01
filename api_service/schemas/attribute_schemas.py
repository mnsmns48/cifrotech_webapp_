from typing import List, Optional

from pydantic import BaseModel, field_validator, ConfigDict

from models.attributes import OverrideType


class AttributeBase(BaseModel):
    attribute_name: str
    alias: str | None

    @field_validator("attribute_name")
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Attribute name cannot be empty")
        return v

    @field_validator("alias")
    def validate_alias(cls, v):
        return v.strip() if v else v


class CreateAttribute(AttributeBase):
    key: int


class UpdateAttribute(AttributeBase):
    id: int


class Brand(BaseModel):
    id: int
    brand: str

    model_config = ConfigDict(from_attributes=True)


class Types(BaseModel):
    id: int
    type: str
    model_config = ConfigDict(from_attributes=True)


class AttributeKey(BaseModel):
    id: int
    key: str

    model_config = ConfigDict(from_attributes=True)


class AttributeBrandRule(BaseModel):
    product_type_id: int
    brand_id: int
    attr_key_id: int
    rule_type: OverrideType
    brand: Brand
    attr_key: AttributeKey

    model_config = ConfigDict(from_attributes=True)


class AttributeLink(BaseModel):
    product_type_id: int
    attr_key_id: int
    attr_key: AttributeKey

    model_config = ConfigDict(from_attributes=True)


class AttributeTypesMap(BaseModel):
    id: int
    type: str
    rule_overrides: List[AttributeBrandRule]
    attr_link: List[AttributeLink]

    model_config = ConfigDict(from_attributes=True)


class TypesDependenciesResponse(BaseModel):
    types_map: List[AttributeTypesMap]
    keys: List[AttributeKey]
    brands: List[Brand]

    model_config = ConfigDict(from_attributes=True)


class TypeDependencyLink(BaseModel):
    type_id: int
    attr_key_id: int


class AttributeBrandRuleLink(BaseModel):
    product_type_id: int
    brand_id: int
    attr_key_id: int
    rule_type: OverrideType


class TypeAndBrandPayload(BaseModel):
    type_id: int
    brand_ids: list[int] | None = None
    model_config = ConfigDict(from_attributes=True)


class ProductFeaturesGlobalResponse(BaseModel):
    id: int
    title: str
    type_id: int
    brand_id: int
    brand: str
    model_config = ConfigDict(from_attributes=True)
