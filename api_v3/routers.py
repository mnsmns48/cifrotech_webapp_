import time
from typing import Optional, List

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_miniapp.schemas import HubProductScheme
from api_service.s3_helper import get_url_from_s3
from api_v3.crud import fetch_products_cursor_paginated
from api_v3.filters import generate_filters_hash
from api_v3.menu_resolver import resolve_menu_levels_to_path_ids, build_cursor_response
from engine import db

api_v3 = APIRouter(prefix="/api3", tags=["api_v3"])


@api_v3.get("/products")
async def get_products(cursor: int | None = None,
                       limit: int = 24,
                       menu_levels: List[int] = Query(None),
                       session: AsyncSession = Depends(db.scoped_session_dependency)):
    start = time.monotonic()
    path_ids = await resolve_menu_levels_to_path_ids(menu_levels, session)
    filters = {"menu_levels": menu_levels}
    filters_hash = generate_filters_hash(filters)
    rows = await fetch_products_cursor_paginated(session=session, path_ids=path_ids, cursor=cursor, limit=limit)
    next_cursor, has_more = build_cursor_response(rows, limit)
    products = []
    for row in rows:
        pics = row.get("pics")
        preview = row.get("preview")

        if pics:
            pics = [get_url_from_s3(filename=icon, path=row.get("origin")) for icon in pics]
        if preview:
            preview = get_url_from_s3(filename=preview, path=row.get("origin"))

        transformed = {**row, "pics": pics, "preview": preview}
        products.append(HubProductScheme.model_validate(transformed))

    duration_ms = int((time.monotonic() - start) * 1000)

    return {
        "products": products,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "filters_hash": filters_hash,
        "duration_ms": duration_ms
    }