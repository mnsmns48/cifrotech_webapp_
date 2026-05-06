from typing import List

from sqlalchemy import select, exists, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_service.schemas import HubRoutes, HubMenuLevelSchema, PriceSyncPickedPath, RawOrigin, TypeModel, BrandModel, \
    VSLScheme, SyncPathWOrigins
from app_utils import get_url_from_s3
from config import settings
from models import HUbMenuLevel, VendorSearchLine, HUbStock, ProductFeaturesLink, ParsingLine, ProductImage, \
    ProductOrigin, ProductFeaturesGlobal, ProductType, ProductBrand, AttributeOriginValue


async def fetch_leaf_routes(session: AsyncSession, path_ids: list[int]) -> list[HubRoutes]:
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

    bulk = result.scalars().all()

    not_repeated, unique_lines = set(), list()

    for line in bulk:
        if line.id not in not_repeated:
            not_repeated.add(line.id)
            unique_lines.append(line)
    return unique_lines


async def collect_price_sync_paths(session: AsyncSession, leaf_routes: list[HubRoutes]) -> list[PriceSyncPickedPath]:
    if not leaf_routes:
        return []

    leaf_ids = [leaf.path_id for leaf in leaf_routes]
    rows = (await session.execute(select(HUbStock, VendorSearchLine)
                                  .join(VendorSearchLine, VendorSearchLine.id == HUbStock.vsl_id)
                                  .where(HUbStock.path_id.in_(leaf_ids)))).all()
    vsl_by_path: dict[int, list[VSLScheme]] = dict()

    for stock, vsl_row in rows:
        vsl = VSLScheme.model_validate(vsl_row)
        vsl_by_path.setdefault(stock.path_id, []).append(vsl)

    for path_id, vsl_list in vsl_by_path.items():
        seen = set()
        unique_list = list()
        for vsl in vsl_list:
            if vsl.id not in seen:
                seen.add(vsl.id)
                unique_list.append(vsl)
        vsl_by_path[path_id] = unique_list

    result: list[PriceSyncPickedPath] = list()

    for leaf in leaf_routes:
        result.append(
            PriceSyncPickedPath(path_id=leaf.path_id, route=leaf.route, vsl_list=vsl_by_path.get(leaf.path_id, [])))
    return result


async def fetch_raw_origins_db(payload: List[PriceSyncPickedPath], session: AsyncSession) -> List[SyncPathWOrigins]:
    vsl_ids = list({v.id for item in payload for v in item.vsl_list})

    if not vsl_ids:
        return []

    pfl2 = aliased(ProductFeaturesLink)
    hs2 = aliased(HUbStock)

    model_in_hub_by_feature = (
        select(func.count())
        .select_from(pfl2)
        .join(hs2, and_(hs2.origin == pfl2.origin))
        .where(and_(pfl2.feature_id == ProductFeaturesLink.feature_id))
        .correlate(ProductFeaturesLink)
        .scalar_subquery()
    )

    model_in_hub_by_origin = (select(func.count())
                              .select_from(HUbStock)
                              .where(HUbStock.origin == ParsingLine.origin)
                              .correlate(ParsingLine)
                              .scalar_subquery()
                              )

    model_in_hub = case(
        (ProductFeaturesLink.feature_id.isnot(None),
         model_in_hub_by_feature), else_=model_in_hub_by_origin).label("model_in_hub")

    has_model = case((ProductFeaturesLink.feature_id.isnot(None), 1), else_=0).label("has_model")
    img_count = func.count(ProductImage.id).label("img_count")

    stmt = (
        select(ParsingLine.origin,
               ParsingLine.vsl_id,
               ProductOrigin.title,
               ParsingLine.output_price.label("price"),
               img_count,
               model_in_hub,
               has_model,
               ProductFeaturesGlobal.id.label("model_id"),
               ProductFeaturesGlobal.title.label("model_title"),
               ProductType.id.label("type_id"),
               ProductType.type.label("type_name"),
               ProductBrand.id.label("brand_id"),
               ProductBrand.brand.label("brand_name"))
        .select_from(ParsingLine)
        .join(ProductOrigin, ProductOrigin.origin == ParsingLine.origin)
        .join(ProductImage, ProductImage.origin_id == ProductOrigin.origin, isouter=True)
        .join(ProductFeaturesLink, ProductFeaturesLink.origin == ParsingLine.origin, isouter=True)
        .join(ProductFeaturesGlobal, ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id, isouter=True)
        .join(ProductType, ProductType.id == ProductFeaturesGlobal.type_id, isouter=True)
        .join(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id, isouter=True)
        .join(AttributeOriginValue, AttributeOriginValue.origin_id == ParsingLine.origin, isouter=True)

        .where(ProductOrigin.is_deleted.is_(False))
        .where(ParsingLine.vsl_id.in_(vsl_ids))

        .where(AttributeOriginValue.origin_id.is_(None))

        .group_by(ParsingLine.origin,
                  ParsingLine.vsl_id,
                  ProductOrigin.title,
                  ParsingLine.output_price,
                  ProductFeaturesGlobal.id,
                  ProductFeaturesGlobal.title,
                  ProductType.id,
                  ProductType.type,
                  ProductBrand.id,
                  ProductBrand.brand,
                  model_in_hub,
                  has_model)

        .order_by((model_in_hub > 0).desc(),
                  has_model.desc(),
                  ParsingLine.vsl_id,
                  ParsingLine.output_price))

    result = await session.execute(stmt)

    origins: list[RawOrigin] = list()

    for row in result.all():
        origins.append(RawOrigin(origin=row.origin,
                                 title=row.title,
                                 vsl_id=row.vsl_id,
                                 price=row.price,
                                 have_images=row.img_count > 0,
                                 have_attributes=[],
                                 model_id=row.model_id,
                                 model_title=row.model_title,
                                 type_=TypeModel(id=row.type_id, type=row.type_name) if row.type_id else None,
                                 brand=BrandModel(id=row.brand_id,
                                                  brand=row.brand_name) if row.brand_id else None,
                                 model_in_hub=row.model_in_hub > 0)
                       )

    return origins
