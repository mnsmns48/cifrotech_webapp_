import math
import time
from typing import List

from fastapi import APIRouter, Query, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
# from api_service.func import collect_unique_models
from api_service.modulars.desc_builder.service import DescBuilder

from api_service.s3_helper import get_url_from_s3
from api_service.schemas import BrandRuleSchema, TypeModel, BrandModel
from api_service.schemas.desc_builder import BlockResponse

from api_v3.crud import (fetch_products_cursor_paginated, get_product_full, fetch_base_attrs, fetch_brand_rules,
                         fetch_category_items)
from api_v3.filters import build_sku_filters, build_model_filters, compute_filters_hash, validate_filters, \
    normalize_filters, match_sku_item, prepare_model_specs_map, \
    match_model_item, build_meta_filters, match_meta_item
from api_v3.logic import build_cursor_response, build_route, build_attrs, build_images, build_feature_data
from api_v3.menu_tree import MenuTree
from api_v3.schemas import InfiniteProductsResponse, HubProductSchemeExtV3, ProductV3Response, HubLevelSchemeV3, \
    CategoryQuery, CategoryProductsResponse, FiltersResponse, FilterOption, CategoryItem, Pagination
from api_v3.sorting import apply_sort
from cache import get_cache_manager, CacheManager
from cache.keys.filters import model_filters_key
from cache.keys.hub import MENU_LEVELS_CACHE_KEY
from cache.settings import cache_ttl

from engine import db

api_v3 = APIRouter(prefix="/api3", tags=["api_v3"])


@api_v3.get("/init_levels", response_model=List[HubLevelSchemeV3],
            description=("Возвращает список уровней меню каталога. Эндпоинт использует Redis‑кеш для "
                         "ускорения ответа: при наличии сохранённых данных возвращает уровни из кеша, "
                         "а при отсутствии — загружает их из базы, преобразует в сериализуемый формат "
                         "и сохраняет в кеш. Используется для построения дерева категорий и навигации "
                         "по каталогу."))
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency),
                     cache: CacheManager = Depends(get_cache_manager)):
    cached = await cache.get(MENU_LEVELS_CACHE_KEY)
    if cached is not None:
        return [HubLevelSchemeV3(**item) for item in cached]

    levels = await fetch_hub_levels(session)
    raw_levels = [item.model_dump() for item in levels]
    await cache.set(MENU_LEVELS_CACHE_KEY, raw_levels, ttl=cache_ttl.menu)

    return levels


@api_v3.get("/products", response_model=InfiniteProductsResponse,
            description=("Возвращает список товаров, отфильтрованные по уровням меню. "
                         "Использует курсорную пагинацию, возвращает next_cursor, "
                         "флаг has_more, хеш фильтров и время выполнения"))
async def get_products(cursor: int | None = None, limit: int = 24,
                       menu_levels: List[int] = Query(None),
                       session: AsyncSession = Depends(db.scoped_session_dependency),
                       cache: CacheManager = Depends(get_cache_manager)):
    start = time.monotonic()
    tree = MenuTree(session=session)

    path_ids = await tree.resolve_menu_levels_to_path_ids_rt(menu_levels)
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
    tree = MenuTree(session=session, cache=cache)
    route = await build_route(tree, hub_stock.path_id) or []
    type_obj, brand_obj, full_specs, pros_cons, short_specs = await build_feature_data(session, cache, origin_obj)
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
                             short_specs=short_specs,
                             full_specs=full_specs,
                             duration=duration_ms)


@api_v3.get("/category", response_model=CategoryProductsResponse,
            description=("Возвращает данные категории каталога по slug‑пути: хлебные крошки, "
                         "фильтры (SKU и модельные), список товаров с пагинацией, параметры сортировки "
                         "и время обработки запроса. Поддерживает вложенные категории, кеширует дерево "
                         "категорий, уровни меню, модельные фильтры и спецификации товаров для ускорения "
                         "ответа. При отсутствии товаров возвращает пустые фильтры, пустой список товаров "
                         "и заглушки сортировки/пагинации."))
async def get_category_products(request: Request, query: CategoryQuery = Depends(),
                                session: AsyncSession = Depends(db.scoped_session_dependency),
                                cache: CacheManager = Depends(get_cache_manager)):
    start = time.monotonic()
    raw_params = request.query_params
    SERVICE_PARAMS = {"path", "page", "limit", "sort"}

    active_filters_raw = {key: raw_params.getlist(key) for key in raw_params.keys() if key not in SERVICE_PARAMS}
    # tree
    slug_path = query.path.strip("/").split("/")
    tree = MenuTree(session=session, cache=cache)
    category, breadcrumbs, path_ids = await tree.resolve_slug_to_category_and_path_ids(slug_path)
    # items
    items, attribute_index = await fetch_category_items(path_ids, session)
    sort_key = query.sort or "price_asc"

    page = query.page or 1
    limit = query.limit or 24

    if not items:
        pagination = Pagination(page=page, limit=limit, total=0, total_pages=0)
        return CategoryProductsResponse(breadcrumbs=breadcrumbs,
                                        filters=FiltersResponse(meta_filters=[], sku_filters=[], model_filters=[]),
                                        sort=apply_sort([], [], sort_key),
                                        products=[],
                                        filters_hash=compute_filters_hash(slug="/".join(slug_path),
                                                                          active_filters=active_filters_raw,
                                                                          sort_key=sort_key,
                                                                          page=page,
                                                                          limit=limit,
                                                                          model_filters=[],
                                                                          sku_filters=[]),
                                        pagination=pagination,
                                        duration_ms=int((time.monotonic() - start) * 1000))

    feature_ids = {item.feature_id for item in items if item.feature_id}
    specs_map = await DescBuilder.get_short_specs_bulk(list(feature_ids), session, cache)

    model_filters_cache_key = model_filters_key(list(feature_ids))
    cached = await cache.get(model_filters_cache_key)

    if cached:
        model_filters = [FilterOption(**item) for item in cached]
    else:
        model_filters = build_model_filters(specs_map)
        await cache.set(model_filters_cache_key, [f.model_dump() for f in model_filters], ttl=cache_ttl.filters)

    sku_filters = await build_sku_filters(attribute_index)
    meta_filters = await build_meta_filters(items)
    filters_response = FiltersResponse(meta_filters=meta_filters, sku_filters=sku_filters, model_filters=model_filters)

    filters_hash = compute_filters_hash(slug="/".join(slug_path),
                                        active_filters=active_filters_raw,
                                        sort_key=sort_key,
                                        page=page,
                                        limit=limit,
                                        model_filters=[f.model_dump() for f in model_filters],
                                        sku_filters=[f.model_dump() for f in sku_filters])

    normalized_filters = normalize_filters(active_filters_raw, sku_filters, model_filters, meta_filters)
    validated_filters = validate_filters(normalized_filters, sku_filters, model_filters, meta_filters)

    model_specs_map = prepare_model_specs_map(specs_map)

    sku_keys = {f.key for f in sku_filters}
    model_keys = {f.key for f in model_filters}
    meta_keys = {f.key for f in meta_filters}

    filtered_items = list()
    for item in items:
        if not match_sku_item(item, validated_filters, sku_keys):
            continue
        if not match_model_item(item, validated_filters, model_keys, model_specs_map):
            continue
        if not match_meta_item(item, validated_filters, meta_keys):
            continue
        filtered_items.append(item)

    products = [HubProductSchemeExtV3(id=item.hubstock_id,
                                      origin=item.origin,
                                      warranty=item.warranty,
                                      output_price=item.output_price,
                                      title=item.title,
                                      pics=item.pics,
                                      preview=item.preview,
                                      model=item.model,
                                      short_specs=specs_map.get(item.feature_id),
                                      )
                for item in filtered_items
                ]

    sort_response = apply_sort(products, filtered_items, sort_key)
    total = len(products)
    total_pages = math.ceil(total / limit)

    products_page = products[(page - 1) * limit: page * limit]

    pagination = Pagination(page=page, limit=limit, total=total, total_pages=total_pages)

    return CategoryProductsResponse(breadcrumbs=breadcrumbs, filters=filters_response,
                                    sort=sort_response,
                                    products=products_page,
                                    pagination=pagination,
                                    filters_hash=filters_hash,
                                    duration_ms=int((time.monotonic() - start) * 1000))
