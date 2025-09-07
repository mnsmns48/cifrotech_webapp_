from datetime import datetime, timezone
from typing import List, Dict

from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from api_service.crud import delete_product_stock_items, get_all_children_cte, \
    get_origins_by_path_ids, get_info_by_caching, get_lines_by_origins, get_parsing_map, get_hub_map
from api_service.func import generate_diff_tabs
from api_service.s3_helper import get_s3_client, get_http_client_session, sync_images_by_origin

from api_service.schemas import RenameRequest, HubLoadingData, HubItemChangeScheme, OriginsPayload, \
    ComparisonInScheme, HubMenuLevelSchema, HubPositionPatchOut, AddHubLevelScheme, AddHubLevelOutScheme, \
    HubPositionPatch, StockHubItemResult, VSLScheme, ParsingToDiffData, ComparisonOutScheme, ParsingHubDiffOut, \
    HubLevelPath, HubToDiffData

from engine import db
from models import HUbMenuLevel, HUbStock, ProductOrigin, VendorSearchLine

hub_router = APIRouter(tags=['Hub'])


@hub_router.get("/initial_hub_levels", response_model=List[HubMenuLevelSchema])
async def get_hub_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(HUbMenuLevel))
    items = result.scalars().all()
    return items


@hub_router.patch("/rename_hub_level")
async def rename_hub_level_item(payload: RenameRequest, session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(HUbMenuLevel).where(HUbMenuLevel.id == payload.id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Узел не найден")
    if item.label == payload.new_label:
        return {"status": False}
    item.label = payload.new_label
    await session.commit()
    await session.refresh(item)
    return {"status": True, "id": item.id, "new_label": item.label}


@hub_router.patch("/change_hub_item_position", response_model=HubPositionPatchOut)
async def change_hub_item_position(patch: HubPositionPatch,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
    result = await session.execute(select(HUbMenuLevel).where(HUbMenuLevel.id == patch.id))
    moved = result.scalar_one_or_none()
    if not moved:
        raise HTTPException(status_code=404, detail="Узел не найден")

    siblings_result = await session.execute(
        select(HUbMenuLevel)
        .where(HUbMenuLevel.parent_id == patch.parent_id, HUbMenuLevel.id != patch.id)
        .order_by(HUbMenuLevel.sort_order)
    )
    siblings = list(siblings_result.scalars())
    inserted = False

    new_order = list()
    for sibling in siblings:
        new_order.append(sibling)
        if sibling.id == patch.after_id:
            new_order.append(moved)
            inserted = True

    if not inserted:
        new_order.insert(0, moved)

    index_counter = 0
    for item in new_order:
        item.sort_order = index_counter
        item.parent_id = patch.parent_id
        index_counter += 1

    await session.commit()
    await session.refresh(moved)

    return HubPositionPatchOut(status=True, id=moved.id, parent_id=moved.parent_id, sort_order=moved.sort_order)


@hub_router.post("/add_hub_level", response_model=AddHubLevelOutScheme)
async def add_hub_level(payload: AddHubLevelScheme, session: AsyncSession = Depends(db.scoped_session_dependency)):
    query = (select(HUbMenuLevel.sort_order).where(HUbMenuLevel.parent_id == payload.parent_id)
             .order_by(HUbMenuLevel.sort_order.desc()).limit(1))
    result = await session.execute(query)
    max_order = result.scalar_one_or_none() or 0

    new_level = HUbMenuLevel(parent_id=payload.parent_id, label=payload.label, sort_order=max_order + 1)
    session.add(new_level)
    await session.commit()
    return AddHubLevelOutScheme(status=True, id=new_level.id, label=new_level.label,
                                parent_id=new_level.parent_id, sort_order=new_level.sort_order)


@hub_router.delete("/delete_hub_level/{level_id}")
async def delete_hub_level(level_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    level = await session.get(HUbMenuLevel, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Уровень не найден")

    result = await session.execute(select(HUbMenuLevel.id).where(HUbMenuLevel.parent_id == level_id).limit(1))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Нельзя удалить уровень с дочерними элементами"
        )
    parent_id = level.parent_id
    old_order = level.sort_order
    await session.delete(level)
    await session.execute(
        update(HUbMenuLevel)
        .where(HUbMenuLevel.parent_id == parent_id, HUbMenuLevel.sort_order > old_order)
        .values(sort_order=HUbMenuLevel.sort_order - 1)
    )
    await session.commit()
    return {"status": True}


@hub_router.get("/fetch_stock_hub_items/{path_id}", response_model=List[StockHubItemResult])
async def fetch_stock_hub_items(
        path_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = (select(HUbStock, ProductOrigin).join(ProductOrigin, HUbStock.origin == ProductOrigin.origin)
            .where(HUbStock.path_id == path_id).order_by(HUbStock.output_price))
    result = await session.execute(stmt)
    rows = result.all()
    if not rows:
        return []

    origin_ids = [stock.origin for stock, _ in rows]
    features_map = await get_info_by_caching(session, origin_ids)
    items = list()
    for stock, origin in rows:
        items.append(
            StockHubItemResult(
                origin=stock.origin,
                title=origin.title,
                warranty=stock.warranty,
                input_price=stock.input_price,
                output_price=stock.output_price,
                updated_at=stock.updated_at,
                dt_parsed=stock.updated_at,
                features_title=features_map.get(stock.origin, [])
            )
        )
    return items


@hub_router.post("/load_items_in_hub")
async def create_hub_loading(payload: HubLoadingData,
                             session: AsyncSession = Depends(db.scoped_session_dependency),
                             s3_client: AioBaseClient = Depends(get_s3_client),
                             cl_session: ClientSession = Depends(get_http_client_session)):
    vsl = await session.get(VendorSearchLine, payload.vsl_id)
    if not vsl or not vsl.dt_parsed:
        raise HTTPException(status_code=400, detail="Такой vsl_id не найден")

    hub_stock_values = [stock_item.model_dump() for stock_item in payload.stocks]
    for item in hub_stock_values:
        item["vsl_id"] = payload.vsl_id
        item["updated_at"] = vsl.dt_parsed
        item["added_at"] = datetime.now()
    insert_stmt = insert(HUbStock).values(hub_stock_values)
    upsert_stmt = insert_stmt.on_conflict_do_update(index_elements=["origin", "path_id"],
                                                    set_={"warranty": insert_stmt.excluded.warranty,
                                                          "input_price": insert_stmt.excluded.input_price,
                                                          "output_price": insert_stmt.excluded.output_price,
                                                          "updated_at": insert_stmt.excluded.updated_at})
    await session.execute(upsert_stmt)
    await session.commit()
    for item in payload.stocks:
        await sync_images_by_origin(item.origin, session, s3_client, cl_session)
    return {"status": True}


@hub_router.patch("/rename_or_change_price_stock_item")
async def rename_or_change_price_stock_item(patch: HubItemChangeScheme,
                                            session: AsyncSession = Depends(db.scoped_session_dependency)):
    result_origin = await session.execute(select(ProductOrigin).where(ProductOrigin.origin == patch.origin))
    product = result_origin.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="ProductOrigin не найден")

    result_stock = await session.execute(select(HUbStock).where(HUbStock.origin == patch.origin))
    stock = result_stock.scalar_one_or_none()
    if not stock:
        raise HTTPException(status_code=404, detail="HUbStock не найден")

    title_changed, price_changed = False, False

    if patch.title.strip() != product.title:
        product.title = patch.title.strip()
        title_changed = True

    if patch.new_price != stock.output_price:
        stock.output_price = patch.new_price
        stock.updated_at = datetime.now(timezone.utc)
        price_changed = True

    to_update = list()
    if title_changed:
        to_update.append(product)
    if price_changed:
        to_update.append(stock)

    if to_update:
        session.add_all(to_update)
        await session.commit()

    return {"origin": patch.origin,
            "updated": price_changed,
            "new_title": product.title,
            "new_price": stock.output_price,
            "updated_at": stock.updated_at if price_changed else None}


@hub_router.delete("/delete_stock_items")
async def delete_stock_items_endpoint(payload: OriginsPayload,
                                      session: AsyncSession = Depends(db.scoped_session_dependency)) -> bool:
    try:
        await delete_product_stock_items(session, payload.origins)
        return True
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении")


@hub_router.post("/start_comparison_process", response_model=ComparisonOutScheme)
async def comparison_process(payload: ComparisonInScheme,
                             session: AsyncSession = Depends(db.scoped_session_dependency)):
    path_ids: List[HubLevelPath] = await get_all_children_cte(session=session, parent_id=payload.path_id)

    if payload.origins:
        raw_vsl_list: list[VendorSearchLine] = await get_lines_by_origins(origins=payload.origins, session=session)
    else:
        only_paths = [p.path_id for p in path_ids]
        origins = await get_origins_by_path_ids(only_paths, session)
        raw_vsl_list: list[VendorSearchLine] = await get_lines_by_origins(origins, session)

    vsl_list: list[VSLScheme] = list()
    for vsl in raw_vsl_list:
        vsl_list.append(VSLScheme.model_validate(vsl))

    return ComparisonOutScheme(vsl_list=vsl_list, path_ids=path_ids)


@hub_router.post(path="/give_me_consent", response_model=List[ParsingHubDiffOut])
async def consent_process(payload: ComparisonOutScheme,
                          session: AsyncSession = Depends(db.scoped_session_dependency)):
    parsing_map: Dict[int, ParsingToDiffData] = await get_parsing_map(session, payload.vsl_list)
    path_ids: List[int] = [p.path_id for p in payload.path_ids]
    hub_map: Dict[int, List[HubToDiffData]] = await get_hub_map(session, path_ids)
    path_map: Dict[int, str] = dict()
    for p in payload.path_ids:
        path_map.update({p.path_id: p.label})
    result: List[ParsingHubDiffOut] = generate_diff_tabs(parsing_map, hub_map, path_map)
    return result
