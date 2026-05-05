from typing import List

from sqlalchemy import not_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_service.schemas import HubMenuLevelSchema, HubRoutes
from app_utils import get_url_from_s3
from config import settings
from models import HUbMenuLevel


# async def fetch_final_leaf_ids(path_ids: List, session: AsyncSession) -> List:
#     raw_ids: List = [p.path_id for p in path_ids]
#     child = aliased(HUbMenuLevel)
#
#     leaf_condition = not_(exists().where(child.parent_id == HUbMenuLevel.id))
#     leaf_rows = ((await session.execute(select(HUbMenuLevel.id)
#                                         .where(HUbMenuLevel.id.in_(raw_ids)).where(leaf_condition)
#                                         .order_by(HUbMenuLevel.parent_id, HUbMenuLevel.sort_order)))
#                  .mappings().all())
#     leaf_ids: List = [r["id"] for r in leaf_rows]
#
#     return leaf_ids
#
#
# async def fetch_hub_routes_db(path_ids, session) -> List[HubRoutes]:
#     base = (select(HUbMenuLevel.id,
#                    HUbMenuLevel.label,
#                    HUbMenuLevel.icon,
#                    HUbMenuLevel.parent_id,
#                    HUbMenuLevel.sort_order,
#                    HUbMenuLevel.id.label("root_path_id"),
#                    )
#             .where(HUbMenuLevel.id.in_(path_ids))
#             .cte("routes_cte", recursive=True)
#             )
#
#     parent = aliased(HUbMenuLevel)
#
#     recursive = (select(parent.id,
#                         parent.label,
#                         parent.icon,
#                         parent.parent_id,
#                         parent.sort_order,
#                         base.c.root_path_id,
#                         )
#                  .join(base, parent.id == base.c.parent_id)
#                  .where(parent.parent_id != 0))
#
#     routes_cte = base.union_all(recursive)
#
#     rows = ((await session.execute(
#         select(routes_cte)))
#             .mappings().all())
#
#     grouped = dict()
#     for r in rows:
#         grouped.setdefault(r["root_path_id"], []).append(r)
#
#     result: List[HubRoutes] = list()
#
#     for path_id in path_ids:
#         nodes = grouped.get(path_id, [])
#
#         route = [
#             HubMenuLevelSchema(id=n["id"],
#                                sort_order=n["sort_order"],
#                                label=n["label"],
#                                icon=get_url_from_s3(filename=n["icon"], path=settings.s3.utils_path)
#                                if n["icon"] else None,
#                                parent_id=n["parent_id"],
#                                )
#             for n in nodes
#         ]
#
#         route.reverse()
#         result.append(
#             HubRoutes(
#                 path_id=path_id,
#                 route=route
#             )
#         )
#
#     return result

async def fetch_leaf_routes(path_ids: list[int], session: AsyncSession) -> list[HubRoutes]:
    down_base = (select(HUbMenuLevel.id,
                        HUbMenuLevel.label,
                        HUbMenuLevel.icon,
                        HUbMenuLevel.parent_id,
                        HUbMenuLevel.sort_order,
                        HUbMenuLevel.id.label("root_id"))
                 .where(HUbMenuLevel.id.in_(path_ids))
                 .cte("down_cte", recursive=True))
    child = aliased(HUbMenuLevel)
    down_recursive = (select(child.id,
                             child.label,
                             child.icon,
                             child.parent_id,
                             child.sort_order,
                             down_base.c.root_id)
                      .join(down_base, child.parent_id == down_base.c.id))
    down_cte = down_base.union_all(down_recursive)
    leaf_alias = aliased(HUbMenuLevel)
    leaf_condition = ~exists().where(leaf_alias.parent_id == down_cte.c.id)
    leaf_rows = (await session.execute(select(down_cte.c.id,
                                              down_cte.c.label,
                                              down_cte.c.icon,
                                              down_cte.c.parent_id,
                                              down_cte.c.sort_order,
                                              down_cte.c.root_id)
                                       .where(leaf_condition))).mappings().all()
    leaf_ids = [r["id"] for r in leaf_rows]

    if not leaf_ids:
        return []

    up_base = (select(HUbMenuLevel.id,
                      HUbMenuLevel.label,
                      HUbMenuLevel.icon,
                      HUbMenuLevel.parent_id,
                      HUbMenuLevel.sort_order,
                      HUbMenuLevel.id.label("leaf_id")).where(HUbMenuLevel.id.in_(leaf_ids))
               .cte("up_cte", recursive=True))
    parent = aliased(HUbMenuLevel)
    up_recursive = (select(parent.id,
                           parent.label,
                           parent.icon,
                           parent.parent_id,
                           parent.sort_order,
                           up_base.c.leaf_id)
                    .join(up_base, parent.id == up_base.c.parent_id).where(parent.parent_id != 0))

    up_cte = up_base.union_all(up_recursive)

    rows = (await session.execute(select(up_cte))).mappings().all()

    grouped = dict()
    for r in rows:
        grouped.setdefault(r["leaf_id"], []).append(r)

    result: list[HubRoutes] = list()

    for leaf_id, nodes in grouped.items():
        nodes_sorted = sorted(nodes, key=lambda x: x["sort_order"])

        route = [HubMenuLevelSchema(id=n["id"],
                                    sort_order=n["sort_order"],
                                    label=n["label"],
                                    icon=get_url_from_s3(filename=n["icon"],
                                                         path=settings.s3.utils_path) if n["icon"] else None,
                                    parent_id=n["parent_id"]) for n in nodes_sorted]
        result.append(HubRoutes(path_id=leaf_id, route=route))

    return result
