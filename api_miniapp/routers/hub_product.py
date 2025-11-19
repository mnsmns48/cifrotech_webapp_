import time
from typing import List

from fastapi import APIRouter, Depends, Query
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels, fetch_products_by_path
from api_miniapp.schemas import HubLevelScheme, HubProductScheme, HubProductResponse
from api_miniapp.utils import get_pathname_icon_url
from engine import db

hub_product = APIRouter()


@hub_product.get("/hub_levels", response_model=List[HubLevelScheme])
@cache(expire=10)
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)


@hub_product.get("/products_by_path_ids", response_model=HubProductResponse)
@cache(expire=300)
async def products_by_path(ids: list[int] = Query(...), session: AsyncSession = Depends(db.scoped_session_dependency)):
    start = time.monotonic()

    products = await fetch_products_by_path(ids, session)
    result = list()

    for product in products:
        pics = product.get("pics")
        preview = product.get("preview")
        model = product.get("model")

        if pics:
            pics = [get_pathname_icon_url(icon=icon, path=product.get("origin")) for icon in pics]
        if preview:
            preview = get_pathname_icon_url(icon=preview, path=product.get("origin"))

        transformed = {**product, "pics": pics, "preview": preview, "model": model}
        result.append(HubProductScheme.model_validate(transformed))

    duration_ms = int((time.monotonic() - start) * 1000)

    return HubProductResponse(products=result, duration_ms=duration_ms)
