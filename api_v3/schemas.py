from pydantic import BaseModel

from api_miniapp.schemas import HubProductScheme


class ProductResponse(BaseModel):
    products: list[HubProductScheme]
    next_cursor: int | None = None
    has_more: bool
    filters_hash: str
    duration_ms: int
