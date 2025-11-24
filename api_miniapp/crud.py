from typing import Sequence
from sqlalchemy import select, literal, func, case, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app_utils import get_url_from_s3
from config import settings
from models import HUbMenuLevel, HUbStock, ProductOrigin, ProductImage, ProductFeaturesGlobal, ProductFeaturesLink, \
    ServiceImage


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
            row_dict["icon"] = get_url_from_s3(filename=row_dict["icon"], path=settings.s3.utils_path)
        data.append(row_dict)

    return data


async def fetch_products_by_path(path_ids: list, session: AsyncSession) -> Sequence[RowMapping]:
    stmt = (
        select(
            HUbStock.id,
            HUbStock.origin,
            HUbStock.warranty,
            HUbStock.output_price,
            ProductOrigin.title,
            func.array_agg(ProductImage.key).filter(ProductImage.key.isnot(None)).label("pics"),
            func.max(case((ProductImage.is_preview.is_(True), ProductImage.key))).label("preview"),
            ProductFeaturesGlobal.title.label("model"),
        )
        .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
        .outerjoin(ProductImage, ProductImage.origin_id == ProductOrigin.origin)
        .outerjoin(ProductFeaturesLink, ProductFeaturesLink.origin == ProductOrigin.origin)
        .outerjoin(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
        .where(
            HUbStock.path_id.in_(path_ids),
            ProductOrigin.is_deleted.is_(False)
        )
        .group_by(HUbStock.id, ProductOrigin.title, ProductFeaturesGlobal.title)
        .order_by(HUbStock.output_price)
    )

    execute = await session.execute(stmt)
    rows = execute.mappings().all()
    return rows


async def fetch_no_img_pic(session: AsyncSession, var: str):
    stmt = select(ServiceImage).where(ServiceImage.var == var)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_features_by_origin(session: AsyncSession, origin_id: int):
    stmt = (select(ProductFeaturesGlobal)
            .join(ProductFeaturesLink, ProductFeaturesLink.feature_id == ProductFeaturesGlobal.id)
            .where(ProductFeaturesLink.origin == origin_id)
            .order_by(ProductFeaturesGlobal.id))

    result = await session.execute(stmt)
    return result.scalars().all()
