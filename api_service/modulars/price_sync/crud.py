from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_service.schemas import HubRoutes, HubMenuLevelSchema
from app_utils import get_url_from_s3
from config import settings
from models import HUbMenuLevel, VendorSearchLine, HUbStock


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


async def get_vsl_by_origins(origins: list[int], session: AsyncSession) -> list[VendorSearchLine]:
    stmt = (select(VendorSearchLine)
            .join(HUbStock, VendorSearchLine.id == HUbStock.vsl_id).where(HUbStock.origin.in_(origins)))
    result = await session.execute(stmt)
    not_repeated, unique_lines = set(), list()
    bulk = result.scalars().all()
    for line in bulk:
        if line.id not in not_repeated:
            not_repeated.add(line.id)
            unique_lines.append(line)
    return unique_lines


async def get_origins_by_path_ids(path_ids: list | Sequence, session: AsyncSession) -> list[int]:
    stmt = select(HUbStock.origin).where(HUbStock.path_id.in_(path_ids))
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]
