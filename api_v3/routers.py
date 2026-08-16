import time
from typing import List

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
from api_miniapp.schemas import HubLevelScheme
from api_service.modulars.desc_builder.service import DescBuilder

from api_service.s3_helper import get_url_from_s3
from api_service.schemas import AttributeKeyValueSchema
from api_service.schemas.desc_builder import BlockResponse
from api_v3.crud import fetch_products_cursor_paginated
from api_v3.filters import generate_filters_hash
from api_v3.menu_resolver import resolve_menu_levels_to_path_ids, build_cursor_response
from api_v3.schemas import ProductResponse, HubProductSchemeExtV3
from cache import CacheManager, get_cache_manager
from engine import db

api_v3 = APIRouter(prefix="/api3", tags=["api_v3"])


@api_v3.get("/products",
            response_model=ProductResponse,
            description=("Возвращает список товаров, отфильтрованные по уровням меню. "
                         "Использует курсорную пагинацию, возвращает next_cursor, "
                         "флаг has_more, хеш фильтров и время выполнения."))
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
    feature_ids = [row["feature_id"] for row in rows if row.get("feature_id")]
    unique_feature_ids = list({fid for fid in feature_ids if fid is not None})
    short_specs_map = await DescBuilder.get_short_specs_bulk(feature_ids=unique_feature_ids,
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

    return ProductResponse(products=products, next_cursor=next_cursor, has_more=has_more, filters_hash=filters_hash,
                           duration_ms=duration_ms)


@api_v3.get("/init_levels", response_model=List[HubLevelScheme])
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)
