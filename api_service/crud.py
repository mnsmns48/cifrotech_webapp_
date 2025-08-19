from collections import defaultdict
from typing import Sequence, List, Optional

from sqlalchemy import select, Row, delete, distinct
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_service.schemas import HarvestLineIn
from api_service.utils import normalize_origin
from models import Vendor, Harvest, HarvestLine, ProductOrigin, ProductType, ProductBrand, ProductFeaturesGlobal, \
    ProductFeaturesLink, HUbStock, HubLoading, HUbMenuLevel
from models.vendor import VendorSearchLine, RewardRangeLine, RewardRange


async def get_vendor_by_url(url: str, session: AsyncSession):
    result = await session.execute(select(Vendor).join(Vendor.search_lines).where(VendorSearchLine.url == url))
    vendor = result.scalars().first()
    return vendor


async def store_harvest(data: dict, session: AsyncSession) -> int:
    stmt = insert(Harvest).values(**data).returning(Harvest.id)
    result = await session.execute(stmt)
    harvest_id = result.scalar_one()
    await session.commit()
    return harvest_id


async def store_harvest_line(items: Sequence[HarvestLineIn], session: AsyncSession) -> list[dict]:
    items = [line for line in items if not getattr(line, "is_deleted", False)]
    if not items:
        return []

    normalized_map: dict[int, HarvestLineIn] = dict()
    for line in items:
        origin = normalize_origin(line.origin)
        if not origin:
            continue
        normalized_map[origin] = line

    origins = normalized_map.keys()

    existing_stmt = select(ProductOrigin).where(ProductOrigin.origin.in_(origins))
    existing_rows = await session.execute(existing_stmt)
    scalars_result = existing_rows.scalars()
    existing_map: dict[int, ProductOrigin] = dict()

    for product_line in scalars_result:
        existing_map[product_line.origin] = product_line

    product_origin_value, harvest_line_value, return_list = list(), list(), list()

    for origin, line in normalized_map.items():
        db_row = existing_map.get(origin)
        if db_row and db_row.is_deleted:
            continue
        product_origin_value.append({"origin": origin,
                                     "title": line.title,
                                     "link": line.link,
                                     "pics": line.pics,
                                     "preview": line.preview,
                                     "is_deleted": False})
        harvest_line_value.append({"harvest_id": line.harvest_id,
                                   "origin": origin,
                                   "shipment": line.shipment,
                                   "warranty": line.warranty,
                                   "input_price": line.input_price,
                                   "output_price": line.output_price,
                                   "optional": line.optional})
        if db_row:
            return_list.append(
                line.model_copy(update={"title": db_row.title, "is_deleted": db_row.is_deleted})
            )
        else:
            return_list.append(line)

    if not product_origin_value:
        return [data_obj.model_dump() for data_obj in return_list]

    insert_stmt = insert(ProductOrigin).values(product_origin_value)
    stmt_product_origin = insert_stmt.on_conflict_do_update(index_elements=["origin"],
                                                            set_={"link": insert_stmt.excluded.link,
                                                                  "pics": insert_stmt.excluded.pics,
                                                                  "preview": insert_stmt.excluded.preview})

    stmt_harvest_line = (insert(HarvestLine).values(harvest_line_value)
                         .on_conflict_do_nothing(index_elements=["harvest_id", "origin"]))

    await session.execute(stmt_product_origin)
    await session.execute(stmt_harvest_line)
    await session.commit()

    return [data_obj.model_dump() for data_obj in return_list]


async def delete_harvest_strings_by_vsl_id(session: AsyncSession, vsl_id: int):
    harvest_query = select(Harvest).where(Harvest.vendor_search_line_id == vsl_id)
    harvest_result = await session.execute(harvest_query)
    harvest = harvest_result.scalars().first()
    if not harvest:
        return "Запросов парсинга для этого URL нет"
    await session.delete(harvest)
    await session.commit()
    return "Записи для этого запроса удалены"


async def get_range_rewards_list(session: AsyncSession, range_id: int = None) -> Sequence[
    Row[tuple[int, int, bool, int]]]:
    if range_id is None:
        default_range_query = select(RewardRange.id).where(RewardRange.is_default == True)
        default_range = await session.execute(default_range_query)
        range_id = default_range.scalar()
    if range_id is None:
        return []
    query = select(
        RewardRangeLine.line_from, RewardRangeLine.line_to, RewardRangeLine.is_percent, RewardRangeLine.reward
    ).where(RewardRangeLine.range_id == range_id)
    result = await session.execute(query)
    return result.all()


async def get_rr_obj(session: AsyncSession) -> dict[str, int | str] | None:
    query = select(RewardRange.id, RewardRange.title).where(RewardRange.is_default.is_(True))
    result = await session.execute(query)
    row = result.first()
    if row:
        return {"id": row.id, "title": row.title}


async def get_info_by_caching(session: AsyncSession, origins: list[int]) -> dict:
    stmt = (select(ProductFeaturesLink.origin, ProductFeaturesGlobal.title)
            .join(ProductFeaturesGlobal, ProductFeaturesLink.feature_id == ProductFeaturesGlobal.id)
            .where(ProductFeaturesLink.origin.in_(origins)))
    rows = (await session.execute(stmt)).all()
    result = defaultdict(list)
    for origin, title in rows:
        result[origin].append(title)
    return dict(result)


async def store_one_item(session: AsyncSession, data: dict):
    stmt_type = select(ProductType).where(ProductType.type == data["product_type"])
    product_type = (await session.execute(stmt_type)).scalar()

    if not product_type:
        stmt_type_insert = (
            insert(ProductType).values(type=data["product_type"]).on_conflict_do_nothing(index_elements=["type"]))
        await session.execute(stmt_type_insert)
        product_type = (await session.execute(stmt_type)).scalar()

    stmt_brand = select(ProductBrand).where(ProductBrand.brand == data["brand"])
    product_brand = (await session.execute(stmt_brand)).scalar()

    if not product_brand:
        stmt_brand_insert = (
            insert(ProductBrand).values(brand=data["brand"]).on_conflict_do_nothing(index_elements=["brand"]))
        await session.execute(stmt_brand_insert)
        product_brand = (await session.execute(stmt_brand)).scalar()

    stmt_existing_feature = select(ProductFeaturesGlobal.id).where(ProductFeaturesGlobal.title == data["title"])
    existing_feature_row = await session.execute(stmt_existing_feature)
    feature_id = existing_feature_row.scalar()

    if not feature_id:
        stmt_features = (insert(ProductFeaturesGlobal).values(
            title=data["title"],
            type_id=product_type.id,
            brand_id=product_brand.id,
            info=data["info"],
            pros_cons=data["pros_cons"]
        ).on_conflict_do_nothing(index_elements=["title"]).returning(ProductFeaturesGlobal.id))

        feature_row = await session.execute(stmt_features)
        feature_id = feature_row.scalar()

    await session.commit()
    return feature_id


async def add_dependencies_link(session: AsyncSession, origin: int, feature_id: int):
    stmt_feature_link = (insert(ProductFeaturesLink).values(origin=origin, feature_id=feature_id)
                         .on_conflict_do_nothing(index_elements=["origin", "feature_id"]))
    await session.execute(stmt_feature_link)
    await session.commit()


async def delete_product_stock_items(session: AsyncSession, origins: List):
    if not origins:
        return
    stmt = delete(HUbStock).where(HUbStock.origin.in_(origins))
    await session.execute(stmt)
    await session.commit()


async def get_urls_by_origins(origins, session: AsyncSession):
    stmt = (select(distinct(HubLoading.url)).join(HUbStock, HubLoading.id == HUbStock.loading_id)
            .where(HUbStock.origin.in_(origins)))
    result = await session.execute(stmt)
    urls: List[str] = list(result.scalars().all())
    return urls


async def get_origins_by_path_ids(path_ids: list, session: AsyncSession) -> List[int]:
    stmt = select(HUbStock.origin).where(HUbStock.path_id.in_(path_ids))
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_all_children_cte(session: AsyncSession, parent_id: int):
    base = select(HUbMenuLevel).where(HUbMenuLevel.id == parent_id)
    cte = base.cte(name="menu_cte", recursive=True)
    recursive = select(HUbMenuLevel).where(HUbMenuLevel.parent_id == cte.c.id)
    cte = cte.union_all(recursive)
    query = select(cte)
    result = await session.execute(query)
    return result.scalars().all()
