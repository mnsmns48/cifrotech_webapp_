from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Sequence, Dict

from aiohttp import ClientSession
from redis.asyncio import Redis
from sqlalchemy import delete, update, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.api_connect import get_one_by_dtube
from api_service.schemas import ParsingLinesIn, VSLScheme
from api_service.schemas.hub_schemas import HubLevelPath, HubToDiffData
from api_service.schemas.parsing_schemas import SourceContext, ParsingResultOut, ParsingToDiffData
from api_service.schemas.product_schemas import ProductOriginCreate
from api_service.schemas.range_reward_schemas import RewardRangeResponseSchema, RewardRangeLineSchema
from api_service.utils import normalize_origin
from models import Vendor, ParsingLine, ProductOrigin, ProductType, ProductBrand, ProductFeaturesGlobal, \
    ProductFeaturesLink, HUbStock, HUbMenuLevel
from models.vendor import VendorSearchLine, RewardRangeLine, RewardRange

from sqlalchemy import select


async def get_vendor_and_vsl(session: AsyncSession, vsl_id: int) -> Optional[SourceContext]:
    result = await session.execute(
        select(Vendor, VendorSearchLine).join(VendorSearchLine).where(VendorSearchLine.id == vsl_id)
    )
    row = result.first()
    if row is None:
        return None
    vendor, vsl = row
    return SourceContext(vendor, vsl)


async def store_parsing_lines(
        session: AsyncSession, items: List[ParsingLinesIn], vsl_id: int, profit_range_id: int) -> ParsingResultOut:
    normalized: List[ParsingLinesIn] = list()
    for line in items:
        orig = normalize_origin(line.origin)
        if not orig:
            continue
        line.origin = orig
        normalized.append(line)

    if normalized:
        origins = {ln.origin for ln in normalized}
        product_origin_query = select(ProductOrigin).where(ProductOrigin.origin.in_(origins))
        product_orig_in_db = await session.execute(product_origin_query)
        product_orig_list = product_orig_in_db.scalars().all()
        existing: dict[int, ProductOrigin] = dict()
        for product in product_orig_list:
            existing[product.origin] = product
    else:
        existing = dict()

    filtered, seen_origins = list(), set()

    for line in normalized:
        origin = line.origin
        if (origin in seen_origins) or (origin in existing and existing[origin].is_deleted):
            continue
        seen_origins.add(origin)
        filtered.append(line)

    if not filtered:
        return ParsingResultOut(
            dt_parsed=datetime.now(), profit_range_id=profit_range_id, is_ok=False, parsing_result=[]
        )

    new_product_origin: list[ProductOriginCreate] = list()
    for line in filtered:
        if line.origin in existing:
            continue

        po_create = ProductOriginCreate(origin=line.origin, title=line.title, link=line.link, pics=line.pics,
                                        preview=line.preview, is_deleted=False)
        new_product_origin.append(po_create)
    if new_product_origin:
        new_po_dicts = [po.model_dump() for po in new_product_origin]
        stmt = (
            insert(ProductOrigin)
            .values(new_po_dicts)
            .on_conflict_do_nothing(index_elements=[ProductOrigin.origin])
        )
        await session.execute(stmt)
        for po_data in new_po_dicts:
            existing[po_data["origin"]] = ProductOrigin(**po_data)

    await session.execute(delete(ParsingLine).where(ParsingLine.vsl_id == vsl_id))
    await session.flush()
    inserted_bulk = list()
    for line in filtered:
        inserted_bulk.append({"vsl_id": vsl_id,
                              "origin": line.origin,
                              "shipment": line.shipment,
                              "warranty": line.warranty,
                              "input_price": line.input_price,
                              "output_price": line.output_price,
                              "optional": line.optional})
    await session.execute(insert(ParsingLine).values(inserted_bulk))
    vsl_stmt = (update(VendorSearchLine)
                .where(VendorSearchLine.id == vsl_id).values(dt_parsed=datetime.now(), profit_range_id=profit_range_id))
    await session.execute(vsl_stmt)
    response: List[ParsingLinesIn] = list()
    for line in filtered:
        product_origin = existing[line.origin]
        response.append(
            line.model_copy(
                update={"title": product_origin.title, "link": product_origin.link, "pics": product_origin.pics,
                        "preview": product_origin.preview}))
    await session.flush()
    return ParsingResultOut(
        dt_parsed=datetime.now(), profit_range_id=profit_range_id, parsing_result=response, is_ok=False)


async def append_info(session: AsyncSession,
                      data_lines: list[ParsingLinesIn],
                      sync_features: bool,
                      redis: Redis = None,
                      channel: str = None):
    async with ClientSession() as client_session:
        origins = [item.origin for item in data_lines]
        cached: dict[int, list[str]] = await get_info_by_caching(session, origins)
        missing = set(origins) - set(cached.keys())
        if sync_features and missing:
            if redis and channel:
                await redis.publish(channel, f"data: COUNT={len(missing)}")
            for line in data_lines:
                origin = line.origin
                if origin not in missing:
                    continue
                one_item = await get_one_by_dtube(session=client_session, title=line.title)
                if one_item:
                    feature_id = await store_one_item(session=session, data=one_item)
                    await add_dependencies_link(session=session, origin=origin, feature_id=feature_id)
                    cached[origin] = [one_item.get('title')]
                    if redis and channel:
                        await redis.publish(channel, f"Добавление {one_item.get('title')}")
                else:
                    cached[origin] = []
        if not sync_features:
            for origin in missing:
                cached[origin] = []
        for line in data_lines:
            origin = line.origin
            line.features_title = cached.get(origin, [])
    return data_lines


async def get_rr_obj(session: AsyncSession, range_id: Optional[int] = None) -> Optional[RewardRangeResponseSchema]:
    if range_id is None:
        default_range_query = select(RewardRange.id, RewardRange.title).where(RewardRange.is_default.is_(True))
        default_result = await session.execute(default_range_query)
        default_row = default_result.first()
        if not default_row:
            return None
        range_id = default_row.id
        title = default_row.title
    else:
        range_query = select(RewardRange.id, RewardRange.title).where(RewardRange.id == range_id)
        range_result = await session.execute(range_query)
        range_row = range_result.first()
        if not range_row:
            return None
        title = range_row.title
    lines_query = (select(
        RewardRangeLine.line_from, RewardRangeLine.line_to, RewardRangeLine.is_percent, RewardRangeLine.reward)
                   .where(RewardRangeLine.range_id == range_id))
    lines_result = await session.execute(lines_query)
    lines = [
        RewardRangeLineSchema(line_from=row[0], line_to=row[1], is_percent=row[2], reward=row[3])
        for row in lines_result.all()
    ]
    return RewardRangeResponseSchema(id=range_id, title=title, ranges=lines)


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


async def _get_parsing_result(session: AsyncSession, vsl_id: int) -> List[ParsingLinesIn]:
    stmt = (
        select(ParsingLine, ProductOrigin)
        .join(ProductOrigin, ParsingLine.origin == ProductOrigin.origin)
        .where(
            and_(ParsingLine.vsl_id == vsl_id, ProductOrigin.is_deleted.is_(False))
        ).order_by(ParsingLine.input_price)
    )
    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    parsing_results: List[ParsingLinesIn] = list()
    for parsing_line, origin in rows:
        parsing_results.append(ParsingLinesIn(origin=parsing_line.origin,
                                              title=origin.title,
                                              link=origin.link,
                                              shipment=parsing_line.shipment,
                                              warranty=parsing_line.warranty,
                                              input_price=parsing_line.input_price,
                                              output_price=parsing_line.output_price,
                                              pics=origin.pics,
                                              preview=origin.preview,
                                              optional=parsing_line.optional,
                                              features_title=None))
    return parsing_results


async def get_all_children_cte(session: AsyncSession, parent_id: int) -> List[HubLevelPath]:
    base = select(HUbMenuLevel.id, HUbMenuLevel.label).where(HUbMenuLevel.id == parent_id)
    cte = base.cte(name="menu_cte", recursive=True)
    recursive = select(HUbMenuLevel.id, HUbMenuLevel.label).where(HUbMenuLevel.parent_id == cte.c.id)
    cte = cte.union_all(recursive)
    query = select(cte.c.id, cte.c.label)
    execute = await session.execute(query)
    rows = execute.all()
    result = list()
    for path_id, label in rows:
        result.append(HubLevelPath(path_id=path_id, label=label))
    return result


async def get_lines_by_origins(origins: list[int], session: AsyncSession) -> list[VendorSearchLine]:
    stmt = (select(VendorSearchLine)
            .join(HUbStock, VendorSearchLine.id == HUbStock.vsl_id).where(HUbStock.origin.in_(origins)))
    result = await session.execute(stmt)
    not_repeated, unique_lines = set(), list()
    bulk = result.scalars().all()
    for line in bulk:
        if line.id not in not_repeated:
            not_repeated.add(line.id)
            unique_lines.append(line)
    return unique_lines


async def get_origins_by_path_ids(path_ids: list | Sequence, session: AsyncSession) -> list[int]:
    stmt = select(HUbStock.origin).where(HUbStock.path_id.in_(path_ids))
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def get_parsing_map(session: AsyncSession, vsl_list: List[VSLScheme]) -> Dict[int, ParsingToDiffData]:
    vsl_ids: List[int] = [vsl.id for vsl in vsl_list]
    vsl_map: Dict[int, VSLScheme] = {vsl.id: vsl for vsl in vsl_list}
    query = (select(ParsingLine.origin,
                    ParsingLine.vsl_id,
                    ProductOrigin.title.label("title"),
                    ParsingLine.warranty,
                    ParsingLine.optional,
                    ParsingLine.shipment,
                    ParsingLine.input_price.label("parsing_input_price"),
                    ParsingLine.output_price.label("parsing_output_price"),
                    )
             .join(ProductOrigin, ProductOrigin.origin == ParsingLine.origin)
             .where(ProductOrigin.is_deleted == False, ParsingLine.vsl_id.in_(vsl_ids)))
    execute = await session.execute(query)
    rows = execute.all()
    result: Dict[int, ParsingToDiffData] = {}
    for origin, vsl_id, title, warranty, optional, shipment, parsing_input_price, parsing_output_price in rows:
        vsl = vsl_map[vsl_id]
        data = ParsingToDiffData(origin=origin, title=title, warranty=warranty, optional=optional,
                                 shipment=shipment, parsing_line_title=vsl.title,
                                 parsing_input_price=parsing_input_price,
                                 parsing_output_price=parsing_output_price, dt_parsed=vsl.dt_parsed,
                                 profit_range_id=vsl.profit_range_id)
        result[origin] = data
    return result


async def get_hub_map(session: AsyncSession, path_ids: List[int]) -> Dict[int, List[HubToDiffData]]:
    stmt = (select(HUbStock.origin, HUbStock.path_id, ProductOrigin.title.label("title"),
                   HUbStock.warranty, HUbStock.input_price, HUbStock.output_price, HUbStock.added_at,
                   HUbStock.updated_at)
            .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
            .where(HUbStock.path_id.in_(path_ids), ProductOrigin.is_deleted == False)
            .order_by(HUbStock.output_price))
    execute = await session.execute(stmt)
    rows = execute.all()

    hub_map: Dict[int, List[HubToDiffData]] = dict()
    for origin, title,path_id, warranty, input_obj, output, added_at, updated_at in rows:
        row = HubToDiffData(origin=origin, title=title, warranty=warranty, hub_input_price=input_obj, hub_output_price=output,
                            hub_added_at=added_at, hub_updated_at=updated_at)
        hub_map.setdefault(path_id, []).append(row)

    return hub_map
