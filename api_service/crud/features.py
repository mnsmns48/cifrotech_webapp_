from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from api_service.schemas import HubLevelPath, PathRoutes, OriginHubLevelMap, FeaturesDataSet, FeaturesElement, \
    SetFeaturesHubLevelRequest, SetLevelRoutesResponse, FeatureResponseScheme, ProsConsItem, ProsConsItemUpdate, \
    FeatureCategory, UpdateFeatureCategoryRequest, InnerRowRequest, UpdateInnerRowRequest, FeatureIds, TypesAndBrands, \
    CreateFeaturesGlobal

from api_service.schemas.hub_schemas import PathRoute
from api_service.schemas.product_schemas import BrandModel, TypeModel, OriginsList, ProductOriginUpdate
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


async def get_features_by_origin_db(feature_id: int, session: AsyncSession):
    stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == feature_id)
    result = await session.execute(stmt)
    row = result.scalars().first()

    if not row:
        return FeatureResponseScheme(title="Feature not found", info=[], pros_cons={})

    info_list = row.info if row.info else []
    pros_cons = row.pros_cons if row.pros_cons else {}

    return FeatureResponseScheme(id=row.id, title=row.title, info=info_list, pros_cons=pros_cons)


async def delete_pros_cons_value_db(payload: ProsConsItem, session: AsyncSession):
    stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == payload.id)
    result = await session.execute(stmt)
    feature: ProductFeaturesGlobal | None = result.scalar_one_or_none()

    if not feature:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feature not found")

    if not feature.pros_cons:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pros_cons is empty")

    if payload.attribute not in feature.pros_cons:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Attribute '{payload.attribute}' not found in pros_cons")

    items = feature.pros_cons[payload.attribute]

    if payload.value not in items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Value not found in list")

    updated_items = [v for v in items if v != payload.value]
    new_pros_cons = {**feature.pros_cons, payload.attribute: updated_items}
    feature.pros_cons = new_pros_cons

    await session.commit()
    await session.refresh(feature)

    return {"status": "success", "id": feature.id, "updated": feature.pros_cons}


async def add_pros_cons_value_db(payload: ProsConsItem, session: AsyncSession):
    stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == payload.id)
    result = await session.execute(stmt)
    feature: ProductFeaturesGlobal | None = result.scalar_one_or_none()

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    if not feature.pros_cons:
        feature.pros_cons = {
            "advantage": [],
            "disadvantage": []
        }

    if payload.attribute not in feature.pros_cons:
        raise HTTPException(
            status_code=400,
            detail=f"Attribute '{payload.attribute}' not found in pros_cons"
        )

    items = feature.pros_cons[payload.attribute]
    updated_items = items + [payload.value]
    new_pros_cons = {**feature.pros_cons, payload.attribute: updated_items}
    feature.pros_cons = new_pros_cons

    await session.commit()
    await session.refresh(feature)

    return {"status": "success", "id": feature.id, "updated": feature.pros_cons}


async def update_pros_cons_value_db(payload: ProsConsItemUpdate, session: AsyncSession):
    stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == payload.id)
    result = await session.execute(stmt)
    feature: ProductFeaturesGlobal | None = result.scalar_one_or_none()

    if not feature:
        raise HTTPException(status_code=404, detail="Feature not found")

    if not feature.pros_cons:
        feature.pros_cons = {}

    items = feature.pros_cons.get(payload.attribute, [])

    if payload.old_value not in items:
        raise HTTPException(status_code=400, detail="Old value not found in list")

    updated_items = [payload.new_value if v == payload.old_value else v for v in items]

    new_pros_cons = {**feature.pros_cons, payload.attribute: updated_items}
    feature.pros_cons = new_pros_cons

    await session.commit()
    await session.refresh(feature)

    return {"status": "success", "id": feature.id, "updated": feature.pros_cons}


async def get_feature_or_404(session: AsyncSession, feature_id: int):
    stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == feature_id)
    result = await session.execute(stmt)
    feature = result.scalar_one_or_none()

    if feature is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ProductFeaturesGlobal not found"
        )

    return feature


def normalize_category_info(feature: ProductFeaturesGlobal):
    if feature.info is None:
        return []
    return list(feature.info)


def find_category_index(info: list, category_title: str):
    for i, block in enumerate(info):
        if category_title in block:
            return i
    return None


async def save_feature(session: AsyncSession, feature: ProductFeaturesGlobal):
    await session.commit()
    await session.refresh(feature)
    return feature.info


async def create_new_info_category_db(payload: FeatureCategory, session: AsyncSession):
    feature = await get_feature_or_404(session, payload.id)
    info = normalize_category_info(feature)
    new_title = payload.category_title.strip()

    if not new_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category title cannot be empty"
        )
    index = find_category_index(info, new_title)
    if index is not None:
        return {"status": "exists", "info": info}

    info.append({new_title: {}})
    feature.info = info

    updated_info = await save_feature(session, feature)
    return {"status": "created", "info": updated_info}


async def delete_info_category_db(payload: FeatureCategory, session: AsyncSession):
    feature = await get_feature_or_404(session, payload.id)

    info = normalize_category_info(feature)
    category_title = payload.category_title.strip()

    if not category_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category title cannot be empty"
        )

    index = find_category_index(info, category_title)
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    del info[index]
    feature.info = info

    updated_info = await save_feature(session, feature)
    return {"status": "deleted", "info": updated_info}


async def update_info_category_db(payload: UpdateFeatureCategoryRequest, session: AsyncSession):
    old_title = payload.old_category_title.strip()
    new_title = payload.new_category_title.strip()

    if old_title == new_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Old and new category titles are identical"
        )

    if not new_title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New category title cannot be empty"
        )
    feature = await get_feature_or_404(session, payload.id)
    info = normalize_category_info(feature)
    index = find_category_index(info, old_title)
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Old category not found"
        )
    existing_index = find_category_index(info, new_title)
    if existing_index is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New category title already exists"
        )
    old_block = info[index]
    old_values = old_block[old_title]
    new_block = {new_title: old_values}
    info[index] = new_block
    feature.info = info
    updated_info = await save_feature(session, feature)

    return {"status": "updated", "info": updated_info}


async def add_new_features_inner_row_db(payload: InnerRowRequest, session: AsyncSession):
    feature = await get_feature_or_404(session, payload.id)
    info = normalize_category_info(feature)

    category_block = None
    for block in info:
        if payload.category_title in block:
            category_block = block
            break
    if not category_block:
        return {"status": "error", "message": "Category not found"}
    category_block[payload.category_title][payload.new_param] = payload.new_value
    flag_modified(feature, "info")

    await session.commit()
    await session.refresh(feature)

    return {"status": "created", "info": feature.info}


async def delete_features_inner_row_db(payload: InnerRowRequest, session: AsyncSession):
    feature = await get_feature_or_404(session, payload.id)
    info = normalize_category_info(feature)

    category_block = None
    for block in info:
        if payload.category_title in block:
            category_block = block
            break

    if not category_block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    category_data = category_block[payload.category_title]

    if payload.new_param not in category_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Param not found")

    del category_data[payload.new_param]

    flag_modified(feature, "info")

    await session.commit()
    await session.refresh(feature)

    return {"status": "deleted", "info": feature.info}


async def update_features_inner_row_db(payload: UpdateInnerRowRequest, session: AsyncSession):
    feature = await get_feature_or_404(session, payload.id)
    info = normalize_category_info(feature)
    category_block = None
    for block in info:
        if payload.category_title in block:
            category_block = block
            break

    if not category_block:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    category_data = category_block[payload.category_title]

    if payload.old_param not in category_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Old param not found"
        )

    del category_data[payload.old_param]
    category_data[payload.new_param] = payload.new_value
    flag_modified(feature, "info")

    await session.commit()
    await session.refresh(feature)

    return {"status": "updated", "info": feature.info}


async def delete_feature_db(feature_ids: FeatureIds, session: AsyncSession):
    stmt = delete(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id.in_(feature_ids.feature_ids))
    await session.execute(stmt)
    await session.commit()

    return {"status": "deleted", "ids": feature_ids.feature_ids}


async def types_brands_request_db(session: AsyncSession):
    types_result = await session.execute(select(ProductType))
    types = types_result.scalars().all()
    brands_result = await session.execute(select(ProductBrand))
    brands = brands_result.scalars().all()
    return TypesAndBrands(
        types=[TypeModel(id=t.id, type=t.type) for t in types],
        brands=[BrandModel(id=b.id, brand=b.brand) for b in brands]
    )


async def add_new_type_request_db(title: ProductOriginUpdate, session: AsyncSession):
    try:
        new_type = ProductType(type=title.title)
        session.add(new_type)
        await session.commit()
        await session.refresh(new_type)

        return {"id": new_type.id, "type": new_type.type}

    except IntegrityError:
        await session.rollback()
        return {"error": "Тип с таким названием уже существует"}


async def add_new_brand_request_db(title: ProductOriginUpdate, session: AsyncSession):
    try:
        new_brand = ProductBrand(brand=title.title)
        session.add(new_brand)
        await session.commit()
        await session.refresh(new_brand)

        return {"id": new_brand.id, "brand": new_brand.brand}

    except IntegrityError:
        await session.rollback()
        return {"error": "Бренд с таким названием уже существует"}


async def create_new_feature_global_db(payload: CreateFeaturesGlobal, session: AsyncSession):
    new_feature = ProductFeaturesGlobal(
        title=payload.title,
        type_id=payload.type_obj.id,
        brand_id=payload.brand_obj.id,
        info={},
        pros_cons={},
        source="custom"
    )

    session.add(new_feature)
    await session.commit()
    await session.refresh(new_feature)

    return {"id": new_feature.id,
            "title": new_feature.title,
            "type": {"id": payload.type_obj.id, "type": payload.type_obj.type},
            "brand": {"id": payload.brand_obj.id, "brand": payload.brand_obj.brand},
            "info": new_feature.info,
            "pros_cons": new_feature.pros_cons,
            "source": new_feature.source}
