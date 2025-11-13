from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_miniapp.utils import get_pathname_icon_url
from models import HUbMenuLevel


async def fetch_hub_levels(session: AsyncSession):
    base = select(HUbMenuLevel).where(HUbMenuLevel.parent_id == 1).cte(name="menu_cte", recursive=True)

    child = aliased(HUbMenuLevel, name="child")

    recursive = select(child).join(base, child.parent_id == base.c.id)
    menu_cte = base.union_all(recursive)

    result = await session.execute(select(menu_cte))
    rows = result.mappings().all()

    data = list()
    for row in rows:
        row_dict = dict(row)
        if row_dict.get("icon"):
            row_dict["icon"] = get_pathname_icon_url(row_dict["icon"])
        data.append(row_dict)

    return data
