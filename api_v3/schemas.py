from pydantic import BaseModel

from api_miniapp.schemas import HubProductScheme
from api_service.schemas import AttributeKeyValueSchema
from api_service.schemas.desc_builder import BlockResponse


class HubProductSchemeExtV3(HubProductScheme):
    attrs: list[AttributeKeyValueSchema]
    short_specs: list[BlockResponse] | None = None


class ProductResponse(BaseModel):
    products: list[HubProductSchemeExtV3]
    next_cursor: int | None = None
    has_more: bool
    filters_hash: str
    duration_ms: int
