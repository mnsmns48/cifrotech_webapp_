from typing import Sequence
from sqlalchemy import select, literal, func, case, RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_miniapp.schemas import ProductFeaturesSchema
from app_utils import get_url_from_s3
from config import settings
from models import HUbMenuLevel, HUbStock, ProductOrigin, ProductImage, ProductFeaturesGlobal, ProductFeaturesLink, \
    ServiceImage, ProductType, ProductBrand


async def fetch_hub_levels(session: AsyncSession):
    leaf_levels_with_stock = select(HUbStock.path_id.label("id")).distinct().cte("leaf_levels")
    parent = aliased(HUbMenuLevel)

    valid_tree = (select(HUbMenuLevel.id, HUbMenuLevel.parent_id)
                  .where(HUbMenuLevel.id.in_(select(leaf_levels_with_stock.c.id)))
                  .cte(name="valid_tree", recursive=True)
                  )

    valid_tree_rec = select(parent.id, parent.parent_id).join(valid_tree, valid_tree.c.parent_id == parent.id)
    valid_tree = valid_tree.union_all(valid_tree_rec)

    base = (select(HUbMenuLevel.id,
                   HUbMenuLevel.label,
                   HUbMenuLevel.icon,
                   HUbMenuLevel.parent_id,
                   HUbMenuLevel.sort_order,
                   literal(0).label("depth"))
            .where(HUbMenuLevel.parent_id == 1)
            .cte(name="menu_cte", recursive=True))

    child = aliased(HUbMenuLevel)

    recursive = (select(child.id,
                        child.label,
                        child.icon,
                        child.parent_id,
                        child.sort_order,
                        (base.c.depth + 1).label("depth")).join(base, child.parent_id == base.c.id))
    menu_cte = base.union_all(recursive)

    stmt = (select(menu_cte).where(menu_cte.c.id.in_(select(valid_tree.c.id)))
            .order_by(menu_cte.c.depth, menu_cte.c.sort_order))

    result = await session.execute(stmt)
    rows = result.mappings().all()

    data = list()
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


async def fetch_no_img_pic(session: AsyncSession):
    stmt = select(ServiceImage)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_feature_by_origin(session: AsyncSession, origin_id: int):
    stmt = (
        select(
            ProductFeaturesGlobal,
            ProductType.type.label("type_name"),
            ProductBrand.brand.label("brand_name")
        )
        .join(ProductFeaturesLink, ProductFeaturesLink.feature_id == ProductFeaturesGlobal.id)
        .join(ProductType, ProductType.id == ProductFeaturesGlobal.type_id)
        .join(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id)
        .where(ProductFeaturesLink.origin == origin_id)
        .order_by(ProductFeaturesGlobal.id)
    )

    result = await session.execute(stmt)
    row = result.first()

    if not row:
        return None

    feature, type_name, brand_name = row

    return ProductFeaturesSchema(
        id=feature.id,
        title=feature.title,
        type=type_name,
        brand=brand_name,
        source=feature.source,
        info=feature.info,
        pros_cons=feature.pros_cons,
    )
