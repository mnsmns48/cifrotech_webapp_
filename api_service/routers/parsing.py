import asyncio
from datetime import datetime
from typing import Optional, List, Any
from aiohttp import ClientConnectionError, ClientResponseError
from botocore.exceptions import ClientError, BotoCoreError
from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import JSONResponse
from api_service.api_connect import get_items_by_brand, get_one_by_dtube
from api_service.crud import get_vendor_and_vsl, get_rr_obj, _get_parsing_result, get_or_create_product_type, \
    get_or_create_product_brand, get_or_create_feature, link_origin_to_feature
from api_service.s3_helper import (get_s3_client, get_http_client_session, sync_images_by_origin,
                                   generate_final_image_payload, build_with_preview)
from api_service.schemas import (ParsingRequest, ProductOriginUpdate, ProductDependencyUpdate, ProductResponse,
                                 RecalcPricesRequest)
from api_service.schemas.parsing_schemas import SourceContext, ParsingResultOut, ParsingLinesIn
from api_service.schemas.product_schemas import OriginsList, ProductDependencyBatchUpdate
from api_service.schemas.range_reward_schemas import RewardRangeResponseSchema
from api_service.utils import AppDependencies
from config import settings
from engine import db

from models import ParsingLine, ProductOrigin, ProductType, ProductBrand, ProductFeaturesGlobal
from models.product_dependencies import ProductImage
from models.vendor import VendorSearchLine
from parsing.logic import parsing_core, append_info
from parsing.utils import cost_process

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/start_parsing", response_model=ParsingResultOut)
async def go_parsing(data: ParsingRequest, deps: AppDependencies = Depends()) -> Optional[ParsingResultOut]:
    pubsub_obj = deps.redis.pubsub()
    context: SourceContext = await get_vendor_and_vsl(session=deps.session, vsl_id=data.vsl_id)
    start_time = datetime.now()
    try:
        parsing_data: ParsingResultOut = await parsing_core(
            deps.redis, deps.session, deps.s3_client, data.progress, context, data.sync_features)
        duration = (datetime.now() - start_time).total_seconds()
        parsing_data.duration = duration
    finally:
        await deps.redis.publish(data.progress, "data: COUNT=20")
        await asyncio.sleep(0.5)
        await deps.redis.publish(data.progress, "END")
        await pubsub_obj.unsubscribe(data.progress)
        await pubsub_obj.close()
    return parsing_data


async def fetch_previous_parsing_results(data: ParsingRequest, deps: AppDependencies) -> ParsingResultOut:
    vsl: VendorSearchLine | None = await deps.session.get(VendorSearchLine, data.vsl_id)
    if not vsl:
        raise ValueError(f"Ссылка с id: {data.vsl_id} не найдена")

    parsed_lines: List[ParsingLinesIn] = await _get_parsing_result(session=deps.session, vsl_id=data.vsl_id)
    await append_info(session=deps.session, data_lines=parsed_lines, redis=deps.redis,
                      channel=data.progress, sync_features=data.sync_features)
    await build_with_preview(session=deps.session, data_lines=parsed_lines, s3_client=deps.s3_client)

    first_id, all_same = None, True
    for line in parsed_lines:
        if line.profit_range is None:
            all_same = False
            break
        if first_id is None:
            first_id = line.profit_range.id
        elif line.profit_range.id != first_id:
            all_same = False
            break

    profit_range_id = first_id if all_same else None

    return ParsingResultOut(
        dt_parsed=vsl.dt_parsed, profit_range_id=profit_range_id, is_ok=True, parsing_result=parsed_lines)


@parsing_router.post("/previous_parsing_results")
async def get_previous_results(data: ParsingRequest, deps: AppDependencies = Depends()) -> ParsingResultOut:
    return await fetch_previous_parsing_results(data, deps)


@parsing_router.put("/update_parsing_item/{origin}")
async def update_parsing_item(origin: int, data: ProductOriginUpdate,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = select(ProductOrigin).where(ProductOrigin.origin == int(origin))
    result = await session.execute(stmt)
    product_origin = result.scalar_one_or_none()

    if product_origin is None:
        raise HTTPException(status_code=404, detail="ProductOrigin not found")

    if product_origin.title != data.title:
        product_origin.title = data.title
        await session.commit()
        return {"updated": data.title}


@parsing_router.post("/delete_parsing_items/")
async def delete_parsing_items(origins: list[int], session: AsyncSession = Depends(db.scoped_session_dependency)):
    if not origins:
        raise HTTPException(422, detail="Список origin пуст")
    origin_exist = select(ProductOrigin.origin).where(ProductOrigin.origin.in_(origins))
    result = (await session.execute(origin_exist)).scalars().all()
    if not result:
        raise HTTPException(404, detail="Переданные origin не найдены")
    stmt = update(ProductOrigin).where(ProductOrigin.origin.in_(result)).values(is_deleted=True)
    await session.execute(stmt)
    await session.commit()


@parsing_router.get("/get_parsing_items_dependency_list/{origin}")
async def get_parsing_items_dependency_list(origin: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    stmt = select(ProductOrigin.title).where(ProductOrigin.origin == origin)
    result = await session.execute(stmt)
    title = result.scalar_one_or_none()
    if not title:
        raise HTTPException(status_code=404, detail="origin не найден")
    async with ClientSession() as client_session:
        data = await get_items_by_brand(client_session, title)
    if data is None:
        raise HTTPException(status_code=502, detail="Нет данных")
    return {"items": data}


async def process_dependency_item(item: ProductDependencyUpdate, session: AsyncSession,
                                  type_cache: dict[str, ProductType], brand_cache: dict[str, ProductBrand],
                                  title_cache: dict[str, ProductFeaturesGlobal], ) -> dict[str, Any]:
    prod_type = await get_or_create_product_type(item.product_type, session, type_cache)
    prod_brand = await get_or_create_product_brand(item.brand, session, brand_cache)
    feature = await get_or_create_feature(
        item.title, prod_type.id, prod_brand.id, item.info, item.pros_cons, session, title_cache)
    await link_origin_to_feature(item.origin, feature.id, session)

    return {"origin": item.origin, "feature_id": feature.id}


@parsing_router.post("/update_parsing_item_dependency/")
async def update_parsing_item_dependency(
        batch: ProductDependencyBatchUpdate, session: AsyncSession = Depends(db.scoped_session_dependency)):
    type_cache: dict[str, ProductType] = dict()
    brand_cache: dict[str, ProductBrand] = dict()
    title_cache: dict[str, ProductFeaturesGlobal] = dict()

    success, errors = list(), list()
    for item in batch.items:
        try:
            result = await process_dependency_item(item, session, type_cache, brand_cache, title_cache)
            success.append(result)
        except Exception as e:
            errors.append({"origin": item.origin, "error": str(e)})
    try:
        await session.commit()
    except SQLAlchemyError:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при сохранении зависимостей")

    return {"success": success, "errors": errors}


@parsing_router.get("/load_dependency_details/{title}", response_model=ProductResponse)
async def load_dependency_by_title(title: str):
    async with ClientSession() as session:
        data = await get_one_by_dtube(session, title=title)
        if not data:
            return JSONResponse(status_code=404, content={"detail": "Dependency not found"})
        return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@parsing_router.post("/recalculate_output_prices", response_model=ParsingResultOut)
async def recalculate_reward(recalc_req: RecalcPricesRequest, deps: AppDependencies = Depends()):
    vsl: VendorSearchLine | None = await deps.session.get(VendorSearchLine, recalc_req.vsl_id)
    if not vsl:
        raise HTTPException(404, "VSL не найден")
    ranges: RewardRangeResponseSchema = await get_rr_obj(session=deps.session, range_id=recalc_req.range_id)
    stmt = select(ParsingLine).where(ParsingLine.vsl_id == vsl.id)
    lines = await deps.session.execute(stmt)
    for line in lines.scalars().all():
        inp = line.input_price or 0
        line.output_price = cost_process(inp, ranges.ranges)
        line.profit_range_id = recalc_req.range_id
    await deps.session.commit()
    parsed_lines: List[ParsingLinesIn] = await _get_parsing_result(session=deps.session, vsl_id=recalc_req.vsl_id)
    await append_info(session=deps.session,
                      data_lines=parsed_lines,
                      redis=deps.redis, channel='',
                      sync_features=False)
    await build_with_preview(session=deps.session, data_lines=parsed_lines, s3_client=deps.s3_client)

    return ParsingResultOut(
        dt_parsed=vsl.dt_parsed, profit_range_id=recalc_req.range_id, is_ok=True, parsing_result=parsed_lines)


@parsing_router.get("/fetch_images_62701/{origin}")
async def fetch_images_in_origin(
        origin: int,
        session: AsyncSession = Depends(db.scoped_session_dependency),
        s3_client=Depends(get_s3_client),
        cl_session: ClientSession = Depends(get_http_client_session)):
    return await sync_images_by_origin(origin=origin, session=session, s3_client=s3_client, cl_session=cl_session)


@parsing_router.post("/upload_image/{origin}")
async def upload_image_to_origin(
        origin: int, file: UploadFile = File(...), session: AsyncSession = Depends(db.scoped_session_dependency),
        s3_client=Depends(get_s3_client), cl_session: ClientSession = Depends(get_http_client_session)):
    try:
        result = await session.execute(
            select(ProductOrigin).options(selectinload(ProductOrigin.images)).where(ProductOrigin.origin == origin))
        product = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        raise HTTPException(500, f"Ошибка доступа к базе: {e}")
    if not product:
        raise HTTPException(404, "Товар не найден")
    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{origin}/"
    filename = file.filename
    key = f"{prefix}{filename}"
    try:
        put_url = await s3_client.generate_presigned_url(
            ClientMethod="put_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=600)
        body = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Не удалось подготовить загрузку: {e}")

    try:
        async with cl_session.put(put_url, data=body) as resp:
            resp.raise_for_status()
    except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError) as e:
        raise HTTPException(502, f"S3 upload failed: {e}")

    has_preview = False
    for img in product.images:
        if img.is_preview:
            has_preview = True
            break
    is_preview: bool = not has_preview

    new_img = ProductImage(origin_id=product.origin, key=filename, source_url=None, is_preview=is_preview)
    session.add(new_img)
    await session.commit()
    await session.refresh(product)

    payload = await generate_final_image_payload(product, s3_client, bucket, prefix)
    return {"origin": origin, "preview": payload["preview"], "images": payload["images"]}


@parsing_router.delete("/delete_images/{origin}/{filename}")
async def delete_image(
        origin: int, filename: str,
        session: AsyncSession = Depends(db.scoped_session_dependency), s3_client=Depends(get_s3_client)):
    result = await session.execute(
        select(ProductOrigin).options(selectinload(ProductOrigin.images)).where(ProductOrigin.origin == origin))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Товар не найден")
    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{origin}/"
    key = f"{prefix}{filename}"
    try:
        await s3_client.delete_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Не удалось удалить файл из S3: {e}")
    to_delete = None
    for img in product.images:
        if img.key == filename:
            to_delete = img
            break
    if not to_delete:
        raise HTTPException(404, "Изображение не найдено в базе")
    if to_delete.source_url and product.pics:
        product.pics = [pic for pic in product.pics if pic != to_delete.source_url]
    if to_delete.is_preview:
        product.preview = None
        to_delete.is_preview = False
    product.images.remove(to_delete)
    await session.flush()
    if not product.preview and product.images:
        first_key = product.images[0].key
        for img in product.images:
            is_first = (img.key == first_key)
            img.is_preview = is_first
            if is_first:
                product.preview = img.source_url if img.source_url else None
                break
    await session.commit()
    payload = await generate_final_image_payload(product, s3_client, bucket, prefix)
    return {"origin": origin, "preview": payload["preview"], "images": payload["images"]}


@parsing_router.patch("/set_is_preview_image/{origin}/{filename}")
async def set_preview_image(origin: int, filename: str,
                            session: AsyncSession = Depends(db.scoped_session_dependency),
                            s3_client=Depends(get_s3_client)):
    result = await session.execute(select(ProductOrigin)
                                   .options(selectinload(ProductOrigin.images)).where(ProductOrigin.origin == origin))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Товар не найден")

    target_image = next((img for img in product.images if img.key == filename), None)
    if not target_image:
        raise HTTPException(404, "Изображение не найдено")

    if target_image.is_preview:
        final_images = await generate_final_image_payload(product, s3_client, settings.s3.bucket_name,
                                                          f"{settings.s3.s3_hub_prefix}/{origin}/")
        return {"origin": origin, "preview": product.preview, "images": final_images}

    for img in product.images:
        img.is_preview = False
    target_image.is_preview = True

    await session.commit()

    payload = await generate_final_image_payload(
        product, s3_client, settings.s3.bucket_name, f"{settings.s3.s3_hub_prefix}/{origin}/")

    return {"origin": origin, "preview": payload["preview"], "images": payload["images"]}


@parsing_router.post("/clear-media-data")
async def clear_product_media(payload: OriginsList, session: AsyncSession = Depends(db.scoped_session_dependency)):
    if not payload.origins:
        return {"cleared": []}

    stmt = select(ProductOrigin).where(ProductOrigin.origin.in_(payload.origins))
    result = await session.execute(stmt)
    products = result.scalars().all()

    to_clear = list()
    for product in products:
        if product.pics or product.preview:
            to_clear.append(product.origin)

    if to_clear:
        clear_stmt = update(ProductOrigin).where(ProductOrigin.origin.in_(to_clear)).values(pics=[], preview=None)
        await session.execute(clear_stmt)
        await session.commit()
        return {"cleared": to_clear}
