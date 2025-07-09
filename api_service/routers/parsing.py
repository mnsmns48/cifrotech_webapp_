import asyncio
import os
from typing import List
from urllib.parse import urlparse
from aiohttp import ClientConnectionError, ClientResponseError
import aioboto3
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from aiohttp import ClientSession, ClientTimeout
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Path
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from typing_extensions import Dict

from api_service.api_req import get_items_by_brand, get_one_by_dtube
from api_service.crud import get_vendor_by_url, get_range_rewards_list
from api_service.routers.process_helper import _prepare_harvest_response
from api_service.routers.s3_helper import scan_s3_images, generate_presigned_image_urls, upload_missing_images, \
    get_s3_client, get_http_client_session, ALLOWED_EXTENSIONS
from api_service.schemas import ParsingRequest, ProductOriginUpdate, ProductDependencyUpdate, ProductResponse, \
    RecalcPricesResponse, RecalcPricesRequest
from config import redis_session, settings
from engine import db

from models import Harvest, HarvestLine, ProductOrigin, ProductType, ProductBrand, ProductFeaturesGlobal, \
    ProductFeaturesLink
from models.vendor import VendorSearchLine, RewardRange
from parsing.logic import parsing_core
from parsing.utils import cost_process

parsing_router = APIRouter(tags=['Service-Parsing'])


@parsing_router.post("/start_parsing")
async def go_parsing(data: ParsingRequest,
                     redis=Depends(redis_session),
                     session: AsyncSession = Depends(db.scoped_session_dependency)):
    pubsub_obj = redis.pubsub()
    vendor = await get_vendor_by_url(session=session, url=data.vsl_url)
    try:
        parsing_data: dict = await parsing_core(redis, data, vendor, session, vendor.function)
        if len(parsing_data.get('data')) > 0:
            parsing_data.update({'is_ok': True})
    finally:
        await redis.publish(data.progress, "data: COUNT=20")
        await asyncio.sleep(0.5)
        await redis.publish(data.progress, "END")
        await pubsub_obj.unsubscribe(data.progress)
        await pubsub_obj.close()
    return parsing_data


@parsing_router.post("/previous_parsing_results")
async def get_previous_results(
        data: ParsingRequest, redis=Depends(redis_session),
        session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl_exists = await session.get(VendorSearchLine, data.vsl_id)
    if not vsl_exists:
        raise HTTPException(404, "Vendor_search_line с таким ID не найден")
    harvest = await session.execute(
        select(Harvest, RewardRange)
        .join(RewardRange, Harvest.range_id == RewardRange.id)
        .where(Harvest.vendor_search_line_id == data.vsl_id)
    )
    harvest, reward = harvest.first() or (None, None)
    if not harvest:
        return {
            "response": "not found",
            "is_ok": False,
            "message": "Предыдущих результатов нет, соберите данные заново"
        }

    data_with_info = await _prepare_harvest_response(session=session,
                                                     redis=redis,
                                                     harvest_id=harvest.id,
                                                     sync_features=False)
    return {"is_ok": True,
            "category": harvest.category,
            "datestamp": harvest.datestamp,
            "range_reward": {"id": reward.id,
                             "title": reward.title},
            "data": data_with_info}


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


@parsing_router.post("/update_parsing_item_dependency/")
async def update_parsing_item_dependency(
        data: ProductDependencyUpdate,
        session: AsyncSession = Depends(db.scoped_session_dependency)):
    result_type = await session.execute(
        select(ProductType).where(ProductType.type == data.product_type)
    )
    prod_type = result_type.scalar_one_or_none()
    if not prod_type:
        prod_type = ProductType(type=data.product_type)
        session.add(prod_type)
        await session.flush()

    result_brand = await session.execute(
        select(ProductBrand).where(ProductBrand.brand == data.brand)
    )
    prod_brand = result_brand.scalar_one_or_none()
    if not prod_brand:
        prod_brand = ProductBrand(brand=data.brand)
        session.add(prod_brand)
        await session.flush()

    result_feature = await session.execute(
        select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.title == data.title)
    )
    feature = result_feature.scalar_one_or_none()
    if not feature:
        feature = ProductFeaturesGlobal(
            title=data.title,
            type_id=prod_type.id,
            brand_id=prod_brand.id,
            info=data.info,
            pros_cons=data.pros_cons if isinstance(data.pros_cons, dict) else None,
        )
        session.add(feature)
        await session.flush()

    result_link = await session.execute(select(ProductFeaturesLink).where(ProductFeaturesLink.origin == data.origin))
    existing_link = result_link.scalar_one_or_none()
    if existing_link:
        existing_link.feature_id = feature.id
    else:
        link = ProductFeaturesLink(origin=data.origin, feature_id=feature.id)
        session.add(link)
    try:
        await session.commit()
    except SQLAlchemyError as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Ошибка добавления зависимости")
    return {"result": f"{data.origin} - {feature.id}"}


@parsing_router.get("/load_dependency_details/{title}", response_model=ProductResponse)
async def update_parsing_item_dependency(title: str):
    async with ClientSession() as session:
        data = await get_one_by_dtube(session, title=title)
        if not data:
            return JSONResponse(status_code=404, content={"detail": "Dependency not found"})
        return JSONResponse(content=data, media_type="application/json; charset=utf-8")


@parsing_router.post("/recalculate_output_prices", response_model=RecalcPricesResponse)
async def recalculate_reward(recalc_req: RecalcPricesRequest,
                             redis=Depends(redis_session),
                             session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(VendorSearchLine, recalc_req.vsl_id)
    if not vsl:
        raise HTTPException(404, "VendorSearchLine не найден")
    harvest = (await session.execute(
        select(Harvest).where(Harvest.vendor_search_line_id == recalc_req.vsl_id)
    )).scalars().first()
    if not harvest:
        raise HTTPException(404, "Harvest не найден")
    harvest.range_id = recalc_req.range_id
    await session.flush()
    ranges = await get_range_rewards_list(session=session, range_id=recalc_req.range_id)
    lines = (await session.execute(
        select(HarvestLine).where(HarvestLine.harvest_id == harvest.id)
    )).scalars().all()
    for line in lines:
        inp = line.input_price or 0
        line.output_price = cost_process(inp, ranges)
    await session.commit()
    data_with_info = await _prepare_harvest_response(session=session,
                                                     redis=redis,
                                                     harvest_id=harvest.id,
                                                     sync_features=False)
    return {"is_ok": True,
            "category": harvest.category,
            "datestamp": harvest.datestamp,
            "range_reward": recalc_req.range_id,
            "data": data_with_info}


@parsing_router.get("/fetch_images_62701/{origin}")
async def fetch_images_in_origin(origin: int,
                                 session: AsyncSession = Depends(db.scoped_session_dependency),
                                 s3_client = Depends(get_s3_client),
                                 cl_session: ClientSession = Depends(get_http_client_session)):
    try:
        result = await session.execute(select(ProductOrigin).where(ProductOrigin.origin == origin))
        product = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        raise HTTPException(500, "Ошибка доступа к базе данных")
    if not product:
        raise HTTPException(404, "Товар не найден")
    raw_pics = product.pics or []
    external_urls = list()
    local_keys = set()

    for pic in raw_pics:
        parsed = urlparse(pic)
        name = os.path.basename(parsed.path)
        ext = os.path.splitext(name)[1].lower()

        if pic.startswith("http") and ext in ALLOWED_EXTENSIONS:
            external_urls.append(pic)
        elif not pic.startswith("http") and name and ext in ALLOWED_EXTENSIONS:
            local_keys.add(pic)

    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{origin}/"
    try:
        existing_keys = await scan_s3_images(s3_client, bucket, prefix)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Не удалось получить список файлов: {e}")
    new_keys = set()
    if external_urls:
        try:
            new_keys = await upload_missing_images(external_urls, existing_keys, prefix, bucket, s3_client, cl_session)
        except (ClientError, BotoCoreError, asyncio.TimeoutError) as e:
            raise HTTPException(502, f"Ошибка при дозагрузке изображений: {e}")
    all_keys = existing_keys | new_keys | local_keys
    if not all_keys:
        return {"origin": origin, "preview": None, "images": []}
    try:
        images = await generate_presigned_image_urls(all_keys, prefix, bucket, s3_client)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Не удалось сгенерировать ссылки: {e}")
    return {"origin": origin, "preview": images[0]["url"], "images": images}



@parsing_router.post("/upload_image/{origin}")
async def upload_image_to_origin(origin: int,
                                 file: UploadFile = File(...),
                                 session: AsyncSession = Depends(db.scoped_session_dependency)):
    try:
        result = await session.execute(select(ProductOrigin).where(ProductOrigin.origin == origin))
        product: ProductOrigin = result.scalar_one_or_none()
    except SQLAlchemyError as e:
        raise HTTPException(500, f"Ошибка доступа к базе данных {e}")
    if not product:
        raise HTTPException(404, "Товар не найден")
    cfg = Config(signature_version="s3v4", region_name=settings.s3.region, s3={"addressing_style": "path"})
    endpoint = settings.s3.s3_url.rstrip("/")
    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{origin}/"
    key = f"{prefix}{file.filename}"
    timeout = ClientTimeout(total=30)
    session_s3 = aioboto3.Session()

    try:
        async with session_s3.client(service_name="s3", endpoint_url=endpoint,
            aws_access_key_id=settings.s3.s3_access_key.strip(),
            aws_secret_access_key=settings.s3.s3_secret_access_key.strip(), config=cfg) as s3_client:
            try:
                put_url = await s3_client.generate_presigned_url(ClientMethod="put_object",
                                                                 Params={"Bucket": bucket, "Key": key},
                                                                 ExpiresIn=600)
            except (ClientError, BotoCoreError) as e:
                raise HTTPException(502, f"Cannot presign upload PUT: {e}")
            try:
                body = await file.read()
            except (OSError, RuntimeError) as e:
                raise HTTPException(400, f"Cannot read file: {e}")
            async with ClientSession(timeout=timeout) as http:
                try:
                    resp = await http.put(put_url, data=body)
                    resp.raise_for_status()
                except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError) as e:
                    raise HTTPException(502, f"Upload to S3 failed: {e}")
            all_keys = await scan_s3_images(s3_client, bucket, prefix)
            images: List[Dict[str, str]] = await generate_presigned_image_urls(all_keys, prefix, bucket, s3_client)
    except HTTPException:
        raise HTTPException(500, f"Internal server error: {e}")
    first_url = images[0]["url"] if images else None
    if not product.preview and first_url:
        product.preview = first_url
    session.add(product)
    try:
        await session.commit()
    except SQLAlchemyError as e:
        raise HTTPException(500, f"Ошибка сохранения данных в базе: {e}")
    return JSONResponse({"origin": origin, "uploaded": file.filename, "preview": first_url, "images": images})



@parsing_router.delete("/delete_images/{origin}/{filename}")
async def delete_image(origin: int,
                       filename: str,
                       session: AsyncSession = Depends(db.scoped_session_dependency), s3_client=Depends(get_s3_client)):
    result = await session.execute(select(ProductOrigin).where(ProductOrigin.origin == origin))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Товар не найден")

    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{origin}/"
    key = prefix + filename
    try:
        await s3_client.delete_object(Bucket=bucket, Key=key)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Не удалось удалить файл из S3: {e}")
    kept = [
        pic for pic in (product.pics or [])
        if os.path.basename(urlparse(pic).path) != filename
    ]
    product.pics = kept
    try:
        keys = await scan_s3_images(s3_client, bucket, prefix)
        images = await generate_presigned_image_urls(keys, prefix, bucket, s3_client)
    except (ClientError, BotoCoreError) as e:
        images = []
    new_preview = images[0]["url"] if images else None
    product.preview = new_preview
    session.add(product)
    try:
        await session.commit()
    except SQLAlchemyError:
        raise HTTPException(500, "Ошибка при сохранении данных")
    return {"origin": origin, "preview": new_preview, "images": images}