import time
from typing import List

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
from api_miniapp.schemas import HubLevelScheme
from api_service.modulars.desc_builder.service import DescBuilder

from api_service.s3_helper import get_url_from_s3
from api_service.schemas import AttributeKeyValueSchema, TypeModel, BrandModel
from api_service.schemas.desc_builder import BlockResponse
from api_service.schemas.features_schemas import FeatureProductScheme
from api_v3.cache_module import get_cached_features, set_cached_features
from api_v3.crud import fetch_products_cursor_paginated, get_product_full, get_feature_with_type_brand
from api_v3.filters import generate_filters_hash
from api_v3.logic import resolve_menu_levels_to_path_ids, build_cursor_response, build_route, build_attrs, build_images, \
    build_full_specs, build_pros_cons, build_feature_data
from api_v3.schemas import BatchProductsResponse, HubProductSchemeExtV3, ProductV3Response
from cache import get_cache_manager, CacheManager

from engine import db

api_v3 = APIRouter(prefix="/api3", tags=["api_v3"])


@api_v3.get("/init_levels", response_model=List[HubLevelScheme])
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)


@api_v3.get("/products",
            response_model=BatchProductsResponse,
            description=("Возвращает список товаров, отфильтрованные по уровням меню. "
                         "Использует курсорную пагинацию, возвращает next_cursor, "
                         "флаг has_more, хеш фильтров и время выполнения"))
async def get_products(cursor: int | None = None,
                       limit: int = 24,
                       menu_levels: List[int] = Query(None),
                       session: AsyncSession = Depends(db.scoped_session_dependency),
                       cache: CacheManager = Depends(get_cache_manager)):
    start = time.monotonic()
    path_ids = await resolve_menu_levels_to_path_ids(menu_levels, session)
    filters = {"menu_levels": menu_levels}
    filters_hash = generate_filters_hash(filters)
    rows = await fetch_products_cursor_paginated(session=session, path_ids=path_ids, cursor=cursor, limit=limit)
    next_cursor, has_more = build_cursor_response(rows, limit)
    unique_feature_ids = set()
    for row in rows:
        feature_id = row.get("feature_id")
        if feature_id is not None:
            unique_feature_ids.add(feature_id)
    short_specs_map = await DescBuilder.get_short_specs_bulk(feature_ids=list(unique_feature_ids),
                                                             session=session,
                                                             cache=cache)
    products: List[HubProductSchemeExtV3] = list()
    for row in rows:
        origin = row["origin"]
        feature_id = row["feature_id"]

        pics = row.get("pics")
        preview = row.get("preview")

        if pics:
            pics = [get_url_from_s3(filename=icon, path=origin) for icon in pics]

        if preview:
            preview = get_url_from_s3(filename=preview, path=origin)

        blocks: List[BlockResponse] = short_specs_map.get(feature_id, [])
        attrs: List[AttributeKeyValueSchema] = row["attrs"]

        transformed = {**row,
                       "pics": pics,
                       "preview": preview,
                       "attrs": attrs,
                       "short_specs": blocks}
        products.append(HubProductSchemeExtV3.model_validate(transformed))
    duration_ms = int((time.monotonic() - start) * 1000)

    return BatchProductsResponse(products=products, next_cursor=next_cursor, has_more=has_more,
                                 filters_hash=filters_hash,
                                 duration_ms=duration_ms)


@api_v3.get(
    "/product",
    response_model=ProductV3Response,
    description=(
            "Возвращает полную карточку товара по origin: маршрут категории (route), "
            "базовые данные (цена, гарантия, бренд, тип), атрибуты, изображения, "
            "а также расширенные характеристики и текстовые преимущества/недостатки, "
            "если они заданы для модели."
    ),
)
async def get_product(origin: int,
                      session: AsyncSession = Depends(db.scoped_session_dependency),
                      cache: CacheManager = Depends(get_cache_manager)):
    start = time.monotonic()
    origin_obj = await get_product_full(session, origin)

    if not origin_obj:
        raise HTTPException(404, "Товар с указанным origin не найден")

    if not origin_obj.stocks:
        raise HTTPException(404, "Нет данных о наличии товара")

    hub_stock = origin_obj.stocks[0]
    route = await build_route(session, hub_stock.path_id) or []
    type_obj, brand_obj, full_specs, pros_cons = await build_feature_data(session, cache, origin_obj)
    attrs = build_attrs(origin_obj) or []
    pics, preview = build_images(origin_obj)
    pics = pics or []
    duration_ms = int((time.monotonic() - start) * 1000)

    return ProductV3Response(id=hub_stock.id,
                             origin=origin_obj.origin,
                             route=route,
                             warranty=hub_stock.warranty,
                             output_price=hub_stock.output_price,
                             title=origin_obj.title,
                             updated_at=hub_stock.updated_at,
                             type_obj=type_obj,
                             brand_obj=brand_obj,
                             attrs=attrs,
                             pics=pics,
                             preview=preview,
                             pros_cons=pros_cons,
                             full_specs=full_specs,
                             duration=duration_ms)
