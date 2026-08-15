import time
from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi_cache.decorator import cache
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels, fetch_products_by_path, get_feature_by_origin
from api_miniapp.schemas import HubLevelScheme, HubProductScheme, HubProductResponse
from api_miniapp.schemas.hub_prod_scheme import ProductFeaturesResponse
from api_miniapp.utils import cache_with_duration
from api_service.s3_helper import get_url_from_s3
from api_service.schemas import AttributeKeyValueSchema
from engine import db
from models import AttributeKey

hub_product = APIRouter()


@hub_product.get("/hub_levels", response_model=List[HubLevelScheme])
@cache(expire=180)
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)


@hub_product.get("/products_by_path_ids", response_model=HubProductResponse)
@cache_with_duration(expire=180)
async def products_by_path(ids: list[int] = Query(...), session: AsyncSession = Depends(db.scoped_session_dependency)):
    start = time.monotonic()
    products = await fetch_products_by_path(ids, session)
    result = list()
    for product in products:
        pics = product.get("pics")
        preview = product.get("preview")
        model = product.get("model")
        attrs_raw = product.get("attrs") or []

        if pics:
            pics = [get_url_from_s3(filename=icon, path=product.get("origin")) for icon in pics]
        if preview:
            preview = get_url_from_s3(filename=preview, path=product.get("origin"))

        attrs = [AttributeKeyValueSchema(
            id=a["id"],
            value=a["value"],
            alias=a["alias"],
            key=AttributeKey(
                id=a["key"]["id"],
                key=a["key"]["key"],
                alias=a["key"]["alias"]
            )
        )
            for a in attrs_raw
        ]

        transformed = {**product, "pics": pics, "preview": preview, "model": model, "attrs": attrs}
        result.append(HubProductScheme.model_validate(transformed))

    duration_ms = int((time.monotonic() - start) * 1000)

    return HubProductResponse(products=result, duration_ms=duration_ms)


@hub_product.get("/get_product_features/{origin}", response_model=ProductFeaturesResponse)
@cache(expire=180)
async def get_product_features(origin: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    feature = await get_feature_by_origin(session, origin)
    return ProductFeaturesResponse(features=feature)
