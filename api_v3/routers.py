import time
from typing import Optional, List

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.crud import fetch_hub_levels
from api_miniapp.schemas import HubProductScheme, HubLevelScheme
from api_service.s3_helper import get_url_from_s3
from api_v3.crud import fetch_products_cursor_paginated
from api_v3.filters import generate_filters_hash
from api_v3.menu_resolver import resolve_menu_levels_to_path_ids, build_cursor_response
from api_v3.schemas import ProductResponse
from engine import db

api_v3 = APIRouter(prefix="/api3", tags=["api_v3"])


@api_v3.get("/products", response_model=ProductResponse,
            description=("Возвращает список товаров, отфильтрованные по уровням меню. "
                         "Использует курсорную пагинацию, возвращает next_cursor, "
                         "флаг has_more, хеш фильтров и время выполнения."))
async def get_products(cursor: int | None = None, limit: int = 24,
                       menu_levels: List[int] = Query(None),
                       session: AsyncSession = Depends(db.scoped_session_dependency)):
    start = time.monotonic()
    path_ids = await resolve_menu_levels_to_path_ids(menu_levels, session)
    filters = {"menu_levels": menu_levels}
    filters_hash = generate_filters_hash(filters)
    rows = await fetch_products_cursor_paginated(session=session, path_ids=path_ids, cursor=cursor, limit=limit)
    next_cursor, has_more = build_cursor_response(rows, limit)
    products = list()
    for row in rows:
        pics = row.get("pics")
        preview = row.get("preview")

        if pics:
            pics = [get_url_from_s3(filename=icon, path=row.get("origin")) for icon in pics]
        if preview:
            preview = get_url_from_s3(filename=preview, path=row.get("origin"))

        transformed = {**row, "pics": pics, "preview": preview, "attrs": row["attrs"]}
        products.append(HubProductScheme.model_validate(transformed))

    duration_ms = int((time.monotonic() - start) * 1000)

    return ProductResponse(products=products,
                           next_cursor=next_cursor,
                           has_more=has_more,
                           filters_hash=filters_hash,
                           duration_ms=duration_ms)


@api_v3.get("/init_levels", response_model=List[HubLevelScheme])
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)
