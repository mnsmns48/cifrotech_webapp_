from typing import List

from sqlalchemy import not_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_service.schemas import HubMenuLevelSchema, HubRoutes
from app_utils import get_url_from_s3
from config import settings
from models import HUbMenuLevel


async def fetch_final_leaf_ids(path_ids: List, session: AsyncSession) -> List:
    raw_ids: List = [p.path_id for p in path_ids]
    child = aliased(HUbMenuLevel)

    leaf_condition = not_(exists().where(child.parent_id == HUbMenuLevel.id))
    leaf_rows = ((await session.execute(select(HUbMenuLevel.id)
                                        .where(HUbMenuLevel.id.in_(raw_ids)).where(leaf_condition)
                                        .order_by(HUbMenuLevel.parent_id, HUbMenuLevel.sort_order)))
                 .mappings().all())
    leaf_ids: List = [r["id"] for r in leaf_rows]

    return leaf_ids


async def fetch_hub_routes_db(path_ids, session) -> List[HubRoutes]:
    base = (select(HUbMenuLevel.id,
                   HUbMenuLevel.label,
                   HUbMenuLevel.icon,
                   HUbMenuLevel.parent_id,
                   HUbMenuLevel.sort_order,
                   HUbMenuLevel.id.label("root_path_id"),
                   )
            .where(HUbMenuLevel.id.in_(path_ids))
            .cte("routes_cte", recursive=True)
            )

    parent = aliased(HUbMenuLevel)

    recursive = (select(parent.id,
                        parent.label,
                        parent.icon,
                        parent.parent_id,
                        parent.sort_order,
                        base.c.root_path_id,
                        )
                 .join(base, parent.id == base.c.parent_id)
                 .where(parent.parent_id != 0))

    routes_cte = base.union_all(recursive)

    rows = ((await session.execute(
        select(routes_cte)))
            .mappings().all())

    grouped = dict()
    for r in rows:
        grouped.setdefault(r["root_path_id"], []).append(r)

    result: List[HubRoutes] = list()

    for path_id in path_ids:
        nodes = grouped.get(path_id, [])

        route = [
            HubMenuLevelSchema(id=n["id"],
                               sort_order=n["sort_order"],
                               label=n["label"],
                               icon=get_url_from_s3(filename=n["icon"], path=settings.s3.utils_path)
                               if n["icon"] else None,
                               parent_id=n["parent_id"],
                               )
            for n in nodes
        ]

        route.reverse()
        result.append(
            HubRoutes(
                path_id=path_id,
                route=route
            )
        )

    return result
