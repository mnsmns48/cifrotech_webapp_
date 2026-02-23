from collections import defaultdict
from typing import Dict

from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import HubLevelPath, PathRoutes, OriginHubLevelMap, FeaturesDataSet, FeaturesElement, \
    SetFeaturesHubLevelRequest, SetLevelRoutesResponse

from api_service.schemas.hub_schemas import PathRoute
from api_service.schemas.product_schemas import BrandModel, TypeModel, OriginsList
from models import ProductFeaturesGlobal, ProductBrand, ProductType, HUbMenuLevel
from models.product_dependencies import ProductFeaturesHubMenuLevelLink, ProductFeaturesLink


async def features_hub_level_link_fetch_db(session: AsyncSession) -> FeaturesDataSet:
    stmt = (select(ProductFeaturesGlobal.id.label("feature_id"),
                   ProductFeaturesGlobal.title.label("feature_title"),

                   ProductBrand.id.label("brand_id"),
                   ProductBrand.brand.label("brand_name"),

                   ProductType.id.label("type_id"),
                   ProductType.type.label("type_name"),

                   HUbMenuLevel.id.label("level_id"),
                   HUbMenuLevel.label.label("level_label"),
                   )
            .join(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id)
            .join(ProductType, ProductType.id == ProductFeaturesGlobal.type_id)
            .outerjoin(
        ProductFeaturesHubMenuLevelLink,
        ProductFeaturesHubMenuLevelLink.feature_id == ProductFeaturesGlobal.id
    )
            .outerjoin(
        HUbMenuLevel,
        HUbMenuLevel.id == ProductFeaturesHubMenuLevelLink.hub_level_id
    )
            .order_by(ProductType.id, ProductBrand.brand, ProductFeaturesGlobal.title)
            )

    result = await session.execute(stmt)
    rows = result.mappings().all()

    features = list()

    for row in rows:
        hub_level = None
        if row["level_id"] is not None:
            hub_level = HubLevelPath(
                path_id=row["level_id"],
                label=row["level_label"]
            )

        features.append(
            FeaturesElement(id=row["feature_id"],
                            title=row["feature_title"],
                            brand=BrandModel(id=row["brand_id"], brand=row["brand_name"]),
                            type=TypeModel(id=row["type_id"], type=row["type_name"]),
                            hub_level=hub_level)
        )

    return FeaturesDataSet(features=features)


async def features_hub_level_routes_db(session: AsyncSession) -> PathRoutes:
    result = await session.execute(select(HUbMenuLevel)
                                   .order_by(HUbMenuLevel.parent_id, HUbMenuLevel.label, HUbMenuLevel.sort_order))
    levels = result.scalars().all()
    by_id = {lvl.id: lvl for lvl in levels}
    children = defaultdict(list)
    for lvl in levels:
        children[lvl.parent_id].append(lvl)

    leaf_levels = [lvl for lvl in levels if lvl.id not in children]

    def build_path(level: HUbMenuLevel) -> list[HubLevelPath]:
        path: list[HubLevelPath] = []
        current: HUbMenuLevel = level

        while current:
            path.append(HubLevelPath(path_id=current.id, label=current.label))
            if current.parent_id == 0:
                break
            current = by_id.get(current.parent_id)

        return list(reversed(path))

    routes = [PathRoute(rotes=build_path(leaf)) for leaf in leaf_levels]
    return PathRoutes(routes=routes)


async def features_set_level_routes_db(payload: SetFeaturesHubLevelRequest, session: AsyncSession):
    feature_ids = payload.feature_ids
    hub_level_id = payload.hub_level_id
    label = payload.label

    await session.execute(delete(ProductFeaturesHubMenuLevelLink)
                          .where(ProductFeaturesHubMenuLevelLink.feature_id.in_(feature_ids)))

    stmt = (insert(ProductFeaturesHubMenuLevelLink).values(
        [{"feature_id": fid, "hub_level_id": hub_level_id} for fid in feature_ids]).returning(
        ProductFeaturesHubMenuLevelLink.feature_id,
        ProductFeaturesHubMenuLevelLink.hub_level_id))

    result = await session.execute(stmt)
    await session.commit()

    rows = result.fetchall()

    return SetLevelRoutesResponse(updated={r.feature_id: HubLevelPath(
        path_id=r.hub_level_id, label=label) for r in rows})


async def features_check_features_path_label_link_db(origin_ids: OriginsList,
                                                     session: AsyncSession) -> OriginHubLevelMap:
    stmt = (select(ProductFeaturesLink.origin,
                   ProductFeaturesHubMenuLevelLink.hub_level_id)
            .join(ProductFeaturesHubMenuLevelLink,
                  ProductFeaturesHubMenuLevelLink.feature_id == ProductFeaturesLink.feature_id)
            .where(ProductFeaturesLink.origin.in_(origin_ids.origins))
            )

    result = await session.execute(stmt)
    rows = result.fetchall()

    origin_to_level: Dict[int, int] = {origin: hub_level_id for origin, hub_level_id in rows}

    return OriginHubLevelMap(origin_hub_level_map=origin_to_level)
