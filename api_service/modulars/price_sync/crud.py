from collections import defaultdict
from typing import List

from sqlalchemy import select, exists, func, and_, case, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_service.schemas import HubRoutes, HubMenuLevelSchema, PriceSyncPickedPath, RawOrigin, TypeModel, BrandModel, \
    VSLScheme, SyncPathWOrigins, AttributeKeyValueSchema
from api_service.schemas.price_sync_schemas import SyncPathWModels
from api_service.schemas.product_schemas import OriginWithAttrsPicsAnalyze, ModelForApprove
from app_utils import get_url_from_s3
from config import settings
from models import HUbMenuLevel, VendorSearchLine, HUbStock, ProductFeaturesLink, ParsingLine, ProductImage, \
    ProductOrigin, ProductFeaturesGlobal, ProductType, ProductBrand, AttributeOriginValue, AttributeValue, AttributeKey


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

    vsl_to_path: dict[int, int] = dict()
    for item in payload:
        for v in item.vsl_list:
            vsl_to_path[v.id] = item.path_id

    pfl2 = aliased(ProductFeaturesLink)
    hs2 = aliased(HUbStock)

    model_in_hub_by_feature = (select(func.count())
                               .select_from(pfl2)
                               .join(hs2, and_(hs2.origin == pfl2.origin))
                               .where(and_(pfl2.feature_id == ProductFeaturesLink.feature_id))
                               .correlate(ProductFeaturesLink)
                               .scalar_subquery())
    model_in_hub_by_origin = (select(func.count())
                              .select_from(HUbStock)
                              .where(HUbStock.origin == ParsingLine.origin)
                              .correlate(ParsingLine)
                              .scalar_subquery())

    model_in_hub = case((ProductFeaturesLink.feature_id.isnot(None), model_in_hub_by_feature),
                        else_=model_in_hub_by_origin).label("model_in_hub")
    has_model = case((ProductFeaturesLink.feature_id.isnot(None), 1), else_=0).label("has_model")
    img_count = func.count(ProductImage.id).label("img_count")

    stmt = (
        select(
            ParsingLine.origin,
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
            ProductBrand.brand.label("brand_name")
        )
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
    rows = result.all()

    raw_origins: list[RawOrigin] = list()
    for row in rows:
        raw_origins.append(
            RawOrigin(
                origin=row.origin,
                title=row.title,
                vsl_id=row.vsl_id,
                price=row.price,
                have_images=row.img_count > 0,
                have_attributes=[],
                model_id=row.model_id,
                model_title=row.model_title,
                type_=TypeModel(id=row.type_id, type=row.type_name) if row.type_id else None,
                brand=BrandModel(id=row.brand_id, brand=row.brand_name) if row.brand_id else None,
                model_in_hub=row.model_in_hub > 0
            )
        )

    grouped_by_path: dict[int, list[RawOrigin]] = dict()
    for origin in raw_origins:
        path_id = vsl_to_path.get(origin.vsl_id)
        if path_id is None:
            continue
        grouped_by_path.setdefault(path_id, []).append(origin)

    result_list: list[SyncPathWOrigins] = list()
    for item in payload:
        result_list.append(SyncPathWOrigins(path_id=item.path_id,
                                            route=item.route,
                                            vsl_list=item.vsl_list,
                                            raw_origin_ids=grouped_by_path.get(item.path_id, [])))
    return result_list


async def hubstock_origins_map_by_path_ids(path_ids, session) -> dict[int, set[int]]:
    if not path_ids:
        return {}

    rows = ((await session.execute(select(HUbStock.path_id, HUbStock.origin)
                                   .where(HUbStock.path_id.in_(path_ids)))).mappings().all())
    origins = defaultdict(set)
    for row in rows:
        origins[row["path_id"]].add(row["origin"])

    return dict(origins)


async def load_parsing_origins_map(payload: list[PriceSyncPickedPath], session: AsyncSession) -> dict[int, set[int]]:
    path_to_vsl: dict[int, list[int]] = {item.path_id: [v.id for v in item.vsl_list] for item in payload}
    all_vsl_ids = {v.id for item in payload for v in item.vsl_list}
    if not all_vsl_ids:
        return {item.path_id: set() for item in payload}

    rows = (await session.execute(select(ParsingLine.vsl_id, ParsingLine.origin)
                                  .where(ParsingLine.vsl_id.in_(all_vsl_ids)))).all()

    vsl_to_origins: dict[int, set[int]] = {}
    for vsl_id, origin in rows:
        vsl_to_origins.setdefault(vsl_id, set()).add(origin)

    result: dict[int, set[int]] = {}
    for path_id, vsl_ids in path_to_vsl.items():
        origins = set()
        for vsl_id in vsl_ids:
            origins.update(vsl_to_origins.get(vsl_id, set()))
        result[path_id] = origins

    return result


async def load_origin_feature_map(hubstock_origins: set[int] | None,
                                  parsing_origins: set[int] | None,
                                  session: AsyncSession) -> dict[int, dict[str, int | bool]]:
    hubstock_origins = hubstock_origins or set()
    parsing_origins = parsing_origins or set()

    all_origins = hubstock_origins | parsing_origins
    if not all_origins:
        return {}

    rows = ((await session.execute(select(ProductFeaturesLink.origin, ProductFeaturesLink.feature_id)
                                   .where(ProductFeaturesLink.origin.in_(all_origins)))).mappings().all())

    origin_feature_map: dict[int, dict[str, int | bool]] = dict()

    for row in rows:
        origin = row["origin"]
        feature_id = row["feature_id"]
        origin_feature_map[origin] = {"feature_id": feature_id, "in_hub": origin in hubstock_origins}

    return origin_feature_map


async def load_unique_models_by_origins(origin_feature_map: dict[int, dict[str, int | bool]],
                                        session: AsyncSession) -> list[ModelForApprove]:
    origins = set(origin_feature_map.keys())
    if not origins:
        return []

    rows = ((await session.execute(
        select(
            ParsingLine.origin,
            ParsingLine.input_price,
            ParsingLine.output_price,
            ProductOrigin.title.label("origin_title"),

            ProductFeaturesGlobal.id.label("model_id"),
            ProductFeaturesGlobal.title.label("model_title"),
            ProductFeaturesGlobal.info.label("model_info"),
            ProductFeaturesGlobal.source.label("model_source"),

            ProductType.id.label("type_id"),
            ProductType.type.label("type_name"),

            ProductBrand.id.label("brand_id"),
            ProductBrand.brand.label("brand_name"),

            func.min(ParsingLine.input_price)
            .over(partition_by=ProductFeaturesGlobal.id)
            .label("model_min_price"),
        )
        .join(ProductOrigin, ProductOrigin.origin == ParsingLine.origin)
        .join(ProductFeaturesLink, ProductFeaturesLink.origin == ParsingLine.origin)
        .join(ProductFeaturesGlobal,
              ProductFeaturesGlobal.id == ProductFeaturesLink.feature_id)
        .join(ProductType, ProductType.id == ProductFeaturesGlobal.type_id)
        .join(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id)
        .where(ParsingLine.origin.in_(origins))
        .order_by(text("model_min_price NULLS LAST"))
    )).mappings().all())

    models: dict[int, ModelForApprove] = dict()

    for r in rows:
        origin = r["origin"]
        model_id = r["model_id"]

        if model_id not in models:
            type_obj = TypeModel(id=r["type_id"], type=r["type_name"])
            brand_obj = BrandModel(id=r["brand_id"], brand=r["brand_name"])

            models[model_id] = ModelForApprove(
                id=model_id,
                title=r["model_title"],
                info=r["model_info"],
                source=r["model_source"],
                type_=type_obj,
                brand=brand_obj,
                in_hub=False,
                origins=[],
            )

        origin_item = OriginWithAttrsPicsAnalyze(
            origin=origin,
            title=r["origin_title"],
            input_price=r["input_price"],
            output_price=r["output_price"],
            attrs=None,
            pics=None,
            analyze=None,
        )

        models[model_id].origins.append(origin_item)

        if origin_feature_map[origin]["in_hub"]:
            models[model_id].in_hub = True

    return list(models.values())


async def load_origins_attrs_map(origin_ids: list[int] | set[int],
                                 session: AsyncSession) -> dict[int, list[AttributeKeyValueSchema]]:
    if not origin_ids:
        return {}

    stmt = (select(AttributeOriginValue.origin_id,
                   AttributeValue.id,
                   AttributeValue.value,
                   AttributeValue.alias,
                   AttributeKey.id,
                   AttributeKey.key)
            .join(AttributeOriginValue.attr_value)
            .join(AttributeValue.attr_key)
            .where(AttributeOriginValue.origin_id.in_(origin_ids)))

    rows = (await session.execute(stmt)).all()
    result = defaultdict(list)
    for origin_id, attr_value_id, value, alias, key_id, key_str in rows:
        result[origin_id].append(AttributeKeyValueSchema(id=attr_value_id,
                                                         key=AttributeKey(id=key_id, key=key_str),
                                                         value=value,
                                                         alias=alias))
    return result
