from collections import defaultdict
from typing import Dict

from aiohttp import ClientSession
from fastapi import HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from api_service.api_connect import can_connect, create_new_entity_in_server, create_new_product_in_server, \
    create_pros_cons_value_in_server, update_pros_cons_value_in_server, delete_pros_cons_value_in_server, \
    insert_bulk_data_in_server, create_new_info_category_in_server, delete_info_category_in_server, \
    update_info_category_in_server, create_features_inner_row_in_server, update_features_inner_row_in_server, \
    delete_features_inner_row_in_server
from api_service.schemas import HubLevelPath, PathRoutes, OriginHubLevelMap, FeaturesDataSet, FeaturesElement, \
    SetFeaturesHubLevelRequest, SetLevelRoutesResponse, FeatureResponseScheme, ProsConsItem, ProsConsItemUpdate, \
    FeatureCategory, UpdateFeatureCategoryRequest, InnerRowRequest, UpdateInnerRowRequest, FeatureIds, TypesAndBrands, \
    CreateFeaturesGlobal, BrandModel, TypeModel, OriginsList, PathRoute, FormulaIdObj, \
    SetFeaturesFormulaRequest, SetFormulaResponse, FetchProductInfoRequest, ProductResponse, InsertBulkParams, \
    CreateNewCriteria, CreateNewEntityRequest

from models import ProductFeaturesGlobal, ProductBrand, ProductType, HUbMenuLevel, FormulaExpression, \
    ProductFeaturesFormulaLink, ProductFeaturesHubMenuLevelLink, ProductFeaturesLink


async def product_features_depps_db(session: AsyncSession) -> FeaturesDataSet:
    stmt = (
        select(
            ProductFeaturesGlobal.id.label("feature_id"),
            ProductFeaturesGlobal.title.label("feature_title"),
            ProductFeaturesGlobal.source.label("source"),

            ProductBrand.id.label("brand_id"),
            ProductBrand.brand.label("brand_name"),

            ProductType.id.label("type_id"),
            ProductType.type.label("type_name"),

            HUbMenuLevel.id.label("level_id"),
            HUbMenuLevel.label.label("level_label"),

            FormulaExpression.id.label("formula_id"),
            FormulaExpression.name.label("formula_name"),
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
        .outerjoin(
            ProductFeaturesFormulaLink,
            ProductFeaturesFormulaLink.feature_id == ProductFeaturesGlobal.id
        )
        .outerjoin(
            FormulaExpression,
            FormulaExpression.id == ProductFeaturesFormulaLink.formula_id
        )
        .order_by(ProductType.id, ProductBrand.brand, ProductFeaturesGlobal.title)
    )

    result = await session.execute(stmt)
    rows = result.mappings().all()

    features = list()

    for row in rows:
        hub_level = None
        if row["level_id"] is not None:
            hub_level = HubLevelPath(path_id=row["level_id"], label=row["level_label"])
        formula = None
        if row["formula_id"] is not None:
            formula = FormulaIdObj(id=row["formula_id"], name=row["formula_name"])

        features.append(
            FeaturesElement(id=row["feature_id"],
                            title=row["feature_title"],
                            brand=BrandModel(id=row["brand_id"], brand=row["brand_name"]),
                            type=TypeModel(id=row["type_id"], type=row["type_name"]),
                            hub_level=hub_level,
                            source=row["source"],
                            formula=formula)
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


async def delete_pros_cons_value_db(payload: ProsConsItem, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:
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
        result = await delete_pros_cons_value_in_server(product_title=feature.title,
                                                        attribute=payload.attribute,
                                                        value=payload.value, session=cl_session)
        if result:
            items = feature.pros_cons[payload.attribute]

            if payload.value not in items:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Value not found in list")

            updated_items = [v for v in items if v != payload.value]
            new_pros_cons = {**feature.pros_cons, payload.attribute: updated_items}
            feature.pros_cons = new_pros_cons

            await session.commit()
            await session.refresh(feature)

            return {"status": "success", "id": feature.id, "updated": feature.pros_cons}

    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def add_pros_cons_value_db(payload: ProsConsItem, session: AsyncSession, cl_session: ClientSession):
    is_connected = await can_connect(cl_session)
    if is_connected:
        stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == payload.id)
        result = await session.execute(stmt)
        feature: ProductFeaturesGlobal | None = result.scalar_one_or_none()

        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")

        if not feature.pros_cons:
            feature.pros_cons = {"advantage": [], "disadvantage": []}

        if payload.attribute not in feature.pros_cons:
            raise HTTPException(status_code=400, detail=f"Attribute '{payload.attribute}' not found in pros_cons")

        update_dt_info = await create_pros_cons_value_in_server(product_title=feature.title,
                                                                attribute=payload.attribute,
                                                                value=payload.value, session=cl_session)
        if update_dt_info:
            items = feature.pros_cons[payload.attribute]
            updated_items = items + [payload.value]
            new_pros_cons = {**feature.pros_cons, payload.attribute: updated_items}
            feature.pros_cons = new_pros_cons

            await session.commit()
            await session.refresh(feature)

            return {"status": "success", "id": feature.id, "updated": feature.pros_cons}
    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def update_pros_cons_value_db(payload: ProsConsItemUpdate, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:

        stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == payload.id)
        result = await session.execute(stmt)
        feature: ProductFeaturesGlobal | None = result.scalar_one_or_none()

        if not feature:
            raise HTTPException(status_code=404, detail="Feature not found")

        if not feature.pros_cons:
            feature.pros_cons = {}
        result = await update_pros_cons_value_in_server(product_title=feature.title,
                                                        attribute=payload.attribute,
                                                        value=payload.old_value,
                                                        new_value=payload.new_value,
                                                        session=cl_session)
        if result:
            items = feature.pros_cons.get(payload.attribute, [])

            if payload.old_value not in items:
                raise HTTPException(status_code=400, detail="Old value not found in list")

            updated_items = [payload.new_value if v == payload.old_value else v for v in items]

            new_pros_cons = {**feature.pros_cons, payload.attribute: updated_items}
            feature.pros_cons = new_pros_cons

            await session.commit()
            await session.refresh(feature)

            return {"status": "success", "id": feature.id, "updated": feature.pros_cons}
    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


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


async def create_new_info_category_db(payload: FeatureCategory, session: AsyncSession, cl_session: ClientSession):
    is_connected = await can_connect(cl_session)
    if is_connected:
        feature = await get_feature_or_404(session, payload.id)

        info = normalize_category_info(feature)
        new_title = payload.category_title.strip()

        if not new_title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category title cannot be empty"
            )
        result = await create_new_info_category_in_server(feature_title=feature.title, category=new_title,
                                                          session=cl_session)
        if result:
            index = find_category_index(info, new_title)
            if index is not None:
                return {"status": "exists", "info": info}

            info.append({new_title: {}})
            feature.info = info

            updated_info = await save_feature(session, feature)
            return {"status": "created", "info": updated_info}

    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def delete_info_category_db(payload: FeatureCategory, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:
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

        result = await delete_info_category_in_server(feature_title=feature.title,
                                                      category=category_title,
                                                      session=cl_session)
        if result:
            del info[index]
            feature.info = info

            updated_info = await save_feature(session, feature)
            return {"status": "deleted", "info": updated_info}

    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def update_info_category_db(payload: UpdateFeatureCategoryRequest, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:
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
        result = await update_info_category_in_server(feature_title=feature.title,
                                                      category=old_title,
                                                      new_category=new_title,
                                                      session=cl_session)
        if result:
            old_block = info[index]
            old_values = old_block[old_title]
            new_block = {new_title: old_values}
            info[index] = new_block
            feature.info = info
            updated_info = await save_feature(session, feature)

            return {"status": "updated", "info": updated_info}

    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def add_new_features_inner_row_db(payload: InnerRowRequest, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:
        feature = await get_feature_or_404(session, payload.id)
        info = normalize_category_info(feature)
        result = await create_features_inner_row_in_server(feature_title=feature.title,
                                                           category_title=payload.category_title,
                                                           new_param=payload.new_param,
                                                           new_value=payload.new_value,
                                                           session=cl_session)
        if result:
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
    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def delete_features_inner_row_db(payload: InnerRowRequest, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:
        feature = await get_feature_or_404(session, payload.id)
        info = normalize_category_info(feature)

        category_block = None
        for block in info:
            if payload.category_title in block:
                category_block = block
                break

        if not category_block:
            raise HTTPException(status_code=404, detail="Category not found")

        category_data = category_block[payload.category_title]

        if payload.new_param not in category_data:
            raise HTTPException(status_code=404, detail="Param not found")
        result = await delete_features_inner_row_in_server(feature_title=feature.title,
                                                           category_title=payload.category_title,
                                                           new_param=payload.new_param,
                                                           new_value=payload.new_value,
                                                           session=cl_session)
        if result:
            del category_data[payload.new_param]
            flag_modified(feature, "info")
            await session.commit()
            await session.refresh(feature)
            return {"status": "deleted", "info": feature.info}

    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def update_features_inner_row_db(payload: UpdateInnerRowRequest, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:
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
        result = await update_features_inner_row_in_server(feature_title=feature.title,
                                                           category_title=payload.category_title,
                                                           new_param=payload.new_param,
                                                           new_value=payload.new_value,
                                                           old_param=payload.old_param,
                                                           old_value=payload.old_value,
                                                           session=cl_session)

        if payload.old_param not in category_data:
            raise HTTPException(status_code=404, detail="Old param not found")
        if result:
            del category_data[payload.old_param]
            category_data[payload.new_param] = payload.new_value
            flag_modified(feature, "info")

            await session.commit()
            await session.refresh(feature)

            return {"status": "updated", "info": feature.info}
    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


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


async def add_new_type_request_db(payload: CreateNewCriteria, session: AsyncSession, cl_session: ClientSession):
    is_connected = await can_connect(cl_session)
    if is_connected:
        result = await create_new_entity_in_server(CreateNewEntityRequest(type=payload.title, kind=payload.kind),
                                                   cl_session)
        if result:
            try:
                new_type = ProductType(type=payload.title)
                session.add(new_type)
                await session.commit()
                await session.refresh(new_type)

                return {"id": new_type.id, "type": new_type.type}

            except IntegrityError:
                await session.rollback()
                return {"error": "Тип с таким названием уже существует"}
    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def add_new_brand_request_db(payload: CreateNewCriteria, session: AsyncSession, cl_session: ClientSession):
    is_connected = await can_connect(cl_session)
    if is_connected:
        await create_new_entity_in_server(CreateNewEntityRequest(brand=payload.title, kind=payload.kind), cl_session)
        try:
            new_brand = ProductBrand(brand=payload.title)
            session.add(new_brand)
            await session.commit()
            await session.refresh(new_brand)
            return {"id": new_brand.id, "brand": new_brand.brand}

        except IntegrityError:
            await session.rollback()
            return {"error": "Бренд с таким названием уже существует"}
    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def create_new_feature_global_db(payload: CreateFeaturesGlobal, session: AsyncSession, cl_session):
    is_connected = await can_connect(cl_session)
    if is_connected:
        result = await create_new_product_in_server(payload, cl_session)
        if result:
            new_feature = ProductFeaturesGlobal(title=payload.title, type_id=payload.type_obj.id,
                                                brand_id=payload.brand_obj.id, info={}, pros_cons={}, source="custom")

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
    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")


async def set_feature_formula_dependency_db(payload: SetFeaturesFormulaRequest,
                                            session: AsyncSession) -> SetFormulaResponse:
    await session.execute(
        delete(ProductFeaturesFormulaLink).where(ProductFeaturesFormulaLink.feature_id.in_(payload.feature_ids)))

    stmt = (insert(ProductFeaturesFormulaLink).values(
        [{"feature_id": fid, "formula_id": payload.formula_id} for fid in payload.feature_ids])
    .returning(
        ProductFeaturesFormulaLink.feature_id,
        ProductFeaturesFormulaLink.formula_id)
    )

    result = await session.execute(stmt)
    await session.commit()
    rows = result.fetchall()

    return SetFormulaResponse(updated={
        r.feature_id: FormulaIdObj(id=r.formula_id, name=payload.formula_name) for r in rows}
    )


async def fetch_product_information_db(payload: FetchProductInfoRequest, session: AsyncSession) -> ProductResponse:
    try:
        base_query = (
            select(
                ProductFeaturesGlobal.title,
                ProductBrand.brand,
                ProductType.type,
                ProductFeaturesGlobal.source,
                ProductFeaturesGlobal.info,
                ProductFeaturesGlobal.pros_cons
            )
            .join(ProductBrand, ProductBrand.id == ProductFeaturesGlobal.brand_id)
            .join(ProductType, ProductType.id == ProductFeaturesGlobal.type_id)
        )

        if payload.origin is not None:
            stmt = (
                base_query.join(ProductFeaturesLink, ProductFeaturesLink.feature_id == ProductFeaturesGlobal.id)
                .where(ProductFeaturesLink.origin == payload.origin)
                .limit(1)
            )
        elif payload.features_id is not None:
            stmt = base_query.where(ProductFeaturesGlobal.id == payload.features_id).limit(1)
        else:
            stmt = base_query.where(ProductFeaturesGlobal.title == payload.features_title).limit(1)

        result = await session.execute(stmt)
        row = result.fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Feature not found")

        return ProductResponse(
            title=row.title,
            brand=row.brand,
            product_type=row.type,
            source=row.source,
            info=row.info or {},
            pros_cons=row.pros_cons or {}
        )

    finally:
        await session.close()


async def insert_bulk_params_db(payload: InsertBulkParams, session: AsyncSession,
                                cl_session: ClientSession) -> FeatureResponseScheme:
    is_connected = await can_connect(cl_session)
    if is_connected:
        stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.id == payload.feature_id)
        result = await session.execute(stmt)
        feature = result.scalar_one_or_none()

        if feature is None:
            raise HTTPException(status_code=404, detail=f"Feature id={payload.feature_id} не найден.")

        info = feature.info or []

        if not isinstance(info, list):
            raise HTTPException(status_code=500, detail="Поле info должно быть списком.")

        await insert_bulk_data_in_server(
            feature_title=feature.title,
            bulk=[{"param": b.param, "bulk": b.bulk} for b in payload.bulk],
            session=cl_session
        )

        info = list(info)

        for block in payload.bulk:
            block_name = block.param.strip()
            block_text = block.bulk.strip()

            if not block_name:
                raise HTTPException(status_code=400, detail="Поле 'param' не может быть пустым.")

            parsed = dict()

            for line in block_text.splitlines():
                line = line.strip()
                if not line:
                    continue

                if ":" not in line:
                    raise HTTPException(status_code=400,
                                        detail=f"Неверный формат строки: '{line}'. Ожидается 'параметр: значение'.")

                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if not key or not value:
                    raise HTTPException(status_code=400, detail=f"Неверный формат строки: '{line}'.")

                parsed[key] = value

            info.append({block_name: parsed})

        feature.info = info
        flag_modified(feature, "info")

        await session.commit()
        await session.refresh(feature)

        return FeatureResponseScheme(id=feature.id, title=feature.title, info=info, pros_cons=feature.pros_cons or {})

    raise HTTPException(status_code=503, detail="DigitalTube service Unavailable — сервер временно недоступен")
