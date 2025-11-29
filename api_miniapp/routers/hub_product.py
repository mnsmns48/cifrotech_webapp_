import time
from typing import List
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels, fetch_products_by_path, get_feature_by_origin
from api_miniapp.schemas import HubLevelScheme, HubProductScheme, HubProductResponse
from api_miniapp.schemas.hub_prod_scheme import ProductFeaturesResponse
from api_miniapp.utils import cache_with_duration
from app_utils import get_url_from_s3
from engine import db

hub_product = APIRouter()


@hub_product.get("/hub_levels", response_model=List[HubLevelScheme])
@cache(expire=300)
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)


@hub_product.get("/products_by_path_ids", response_model=HubProductResponse)
@cache_with_duration(expire=300)
async def products_by_path(ids: list[int] = Query(...), session: AsyncSession = Depends(db.scoped_session_dependency)):
    start = time.monotonic()

    products = await fetch_products_by_path(ids, session)
    result = list()

    for product in products:
        pics = product.get("pics")
        preview = product.get("preview")
        model = product.get("model")

        if pics:
            pics = [get_url_from_s3(filename=icon, path=product.get("origin")) for icon in pics]
        if preview:
            preview = get_url_from_s3(filename=preview, path=product.get("origin"))

        transformed = {**product, "pics": pics, "preview": preview, "model": model}
        result.append(HubProductScheme.model_validate(transformed))

    duration_ms = int((time.monotonic() - start) * 1000)

    return HubProductResponse(products=result, duration_ms=duration_ms)


@hub_product.get("/get_product_features/{origin}", response_model=ProductFeaturesResponse)
# @cache(expire=300)
async def get_product_features(origin: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    feature = await get_feature_by_origin(session, origin)
    return ProductFeaturesResponse(features=feature)
