from pydantic import BaseModel, ConfigDict

from api_service.schemas import TypeModel, AttributeKey


class ProductTypeWeightRuleSchema(BaseModel):
    id: int
    product_type: TypeModel
    attr_key: AttributeKey
    weight: float
    value_map: dict | None = None
    description: str | None = None
    enabled: bool

    model_config = ConfigDict(from_attributes=True)
