from sqlalchemy import select, literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_miniapp.utils import get_pathname_icon_url
from models import HUbMenuLevel


async def fetch_hub_levels(session: AsyncSession):
    base = (select(HUbMenuLevel.id,
               HUbMenuLevel.label,
               HUbMenuLevel.icon,
               HUbMenuLevel.parent_id,
               HUbMenuLevel.sort_order,
               literal(0).label("depth")).where(HUbMenuLevel.parent_id == 1).cte(name="menu_cte", recursive=True))

    child = aliased(HUbMenuLevel, name="child")

    recursive = (select(
        child.id, child.label, child.icon, child.parent_id, child.sort_order, (base.c.depth + 1).label("depth"))
                 .join(base, child.parent_id == base.c.id))

    menu_cte = base.union_all(recursive)

    result = await session.execute(
        select(menu_cte).order_by(menu_cte.c.depth, menu_cte.c.sort_order)
    )
    rows = result.mappings().all()

    data = []
    for row in rows:
        row_dict = dict(row)
        if row_dict.get("icon"):
            row_dict["icon"] = get_pathname_icon_url(row_dict["icon"])
        data.append(row_dict)

    return data

#
# async def fetch_products_by_path(path: int, session: AsyncSession):
#