import math
import time
from typing import List, Dict

from fastapi import APIRouter, Query, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
from api_service.modulars.desc_builder.service import DescBuilder

from api_service.s3_helper import get_url_from_s3
from api_service.schemas.desc_builder import BlockResponse

from api_v3.crud import (fetch_products_cursor_paginated, get_product_full,
    # fetch_origins, fetch_feature_ids, fetch_types_brands,
                         fetch_base_attrs, fetch_brand_rules,
                         fetch_category_items)
from api_v3.filters import build_sku_filters, build_model_filters
from api_v3.logic import resolve_menu_levels_to_path_ids, build_cursor_response, build_route, build_attrs, build_images, \
    build_feature_data, resolve_slug_path_to_level, collect_descendants
from api_v3.schemas import InfiniteProductsResponse, HubProductSchemeExtV3, ProductV3Response, HubLevelSchemeV3, \
    CategoryQuery, CategoryProductsResponse, FiltersResponse, FilterOption, CategoryItem, Pagination, SortResponse, \
    SortOption
from cache import get_cache_manager, CacheManager
from cache.keys.filters import model_filters_key
from cache.keys.hub import MENU_LEVELS
from cache.settings import cache_ttl

from engine import db

api_v3 = APIRouter(prefix="/api3", tags=["api_v3"])


@api_v3.get("/init_levels", response_model=List[HubLevelSchemeV3])
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency),
                     cache: CacheManager = Depends(get_cache_manager)):
    cached = await cache.get(MENU_LEVELS)
    if cached is not None:
        return [HubLevelSchemeV3(**item) for item in cached]

    levels = await fetch_hub_levels(session)
    raw_levels = [item.model_dump() for item in levels]
    await cache.set(MENU_LEVELS, raw_levels, ttl=cache_ttl.menu)
    return levels


@api_v3.get("/products",
            response_model=InfiniteProductsResponse,
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

        transformed = {**row,
                       "pics": pics,
                       "preview": preview,
                       "short_specs": blocks}
        products.append(HubProductSchemeExtV3.model_validate(transformed))
    duration_ms = int((time.monotonic() - start) * 1000)

    return InfiniteProductsResponse(products=products, next_cursor=next_cursor, has_more=has_more,
                                    duration_ms=duration_ms)


@api_v3.get("/product",
            response_model=ProductV3Response,
            description=("Возвращает полную карточку товара по origin: маршрут категории (route), "
                         "базовые данные (цена, гарантия, бренд, тип), атрибуты, изображения, "
                         "а также расширенные характеристики и текстовые преимущества/недостатки, "
                         "если они заданы для модели"))
async def get_product(origin: int, session: AsyncSession = Depends(db.scoped_session_dependency),
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


@api_v3.get("/category", response_model=CategoryProductsResponse)
async def get_category_products(
        request: Request,
        query: CategoryQuery = Depends(),
        session: AsyncSession = Depends(db.scoped_session_dependency),
        cache: CacheManager = Depends(get_cache_manager)
):
    start = time.monotonic()
    # raw_params = request.query_params  # пока не используем → можно убрать

    slug_path = query.path.strip("/").split("/")
    category, breadcrumbs = await resolve_slug_path_to_level(slug_path=slug_path, cache=cache, session=session)

    levels_data = await cache.get(MENU_LEVELS)
    if levels_data is None:
        levels = await fetch_hub_levels(session)
        levels_data = [lvl.model_dump() for lvl in levels]
        await cache.set(MENU_LEVELS, levels_data, ttl=cache_ttl.menu)

    levels = [HubLevelSchemeV3(**item) for item in levels_data]
    tree: Dict[int, List[int]] = {}
    for lvl in levels:
        if lvl.parent_id is None:
            continue
        tree.setdefault(lvl.parent_id, []).append(lvl.id)

    path_ids: set[int] = set()
    collect_descendants(tree, category.id, path_ids)

    items: list[CategoryItem] = await fetch_category_items(path_ids, session)

    if not items:
        return CategoryProductsResponse(
            breadcrumbs=breadcrumbs,
            filters=FiltersResponse(sku_filters=[], model_filters=[]),
            products=[],
            duration_ms=int((time.monotonic() - start) * 1000)
        )

    origin_ids = {item.origin for item in items}
    feature_ids = {item.feature_id for item in items if item.feature_id}
    product_type_ids = {item.type.id for item in items if item.type}
    brand_ids = {item.brand.id for item in items if item.brand}

    specs_map = await DescBuilder.get_short_specs_bulk(
        list(feature_ids), session, cache
    )

    model_filters_cache_key = model_filters_key(list(feature_ids))
    cached = await cache.get(model_filters_cache_key)

    if cached:
        model_filters = [FilterOption(**item) for item in cached]
    else:
        model_filters = build_model_filters(specs_map)
        await cache.set(
            model_filters_cache_key,
            [f.model_dump() for f in model_filters],
            ttl=cache_ttl.filters
        )

    base_attrs = await fetch_base_attrs(product_type_ids, session)
    brand_rules = await fetch_brand_rules(product_type_ids, brand_ids, session)

    sku_filters = await build_sku_filters(
        product_type_ids=product_type_ids,
        feature_ids=feature_ids,
        brand_ids=brand_ids,
        base_attrs=base_attrs,
        brand_rules=brand_rules,
        session=session
    )

    products: list[HubProductSchemeExtV3] = [
        HubProductSchemeExtV3(
            id=item.hubstock_id,
            origin=item.origin,
            warranty=item.warranty,
            output_price=item.output_price,
            title=item.title,
            pics=item.pics,
            preview=item.preview,
            model=item.model,
            short_specs=specs_map.get(item.feature_id)
        )
        for item in items
    ]

    # 1. SORTING
    sort_key = query.sort or "price_asc"

    if sort_key == "price_asc":
        products.sort(key=lambda p: (p.output_price or float("inf")))
    elif sort_key == "price_desc":
        products.sort(key=lambda p: -(p.output_price or 0))
    elif sort_key == "newest":
        products.sort(
            key=lambda p: next(i.updated_at for i in items if i.hubstock_id == p.id),
            reverse=True
        )

    sort_response = SortResponse(
        active=sort_key,
        options=[
            SortOption(key="price_asc", label="По возрастанию цены"),
            SortOption(key="price_desc", label="По убыванию цены"),
            SortOption(key="newest", label="Новинки"),
        ]
    )

    # 2. PAGINATION
    page = query.page or 1
    limit = query.limit or 20

    total = len(products)
    start_i = (page - 1) * limit
    end_i = start_i + limit

    products_page = products[start_i:end_i]
    total_pages = math.ceil(total / limit)

    pagination = Pagination(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages
    )

    return CategoryProductsResponse(
        breadcrumbs=breadcrumbs,
        filters=FiltersResponse(
            sku_filters=sku_filters,
            model_filters=model_filters
        ),
        sort=sort_response,
        products=products_page,
        pagination=pagination,
        duration_ms=int((time.monotonic() - start) * 1000)
    )
