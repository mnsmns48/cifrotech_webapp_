import asyncio
import os
from typing import Any

from aiohttp import ClientError as AiohttpClientError
import aioboto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError as BotoClientError
from aiohttp import ClientSession, ClientTimeout
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, and_, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from starlette.responses import JSONResponse

from api_service.api_req import get_items_by_brand, get_one_by_dtube
from api_service.crud import get_vendor_by_url, get_range_rewards_list, get_rr_obj
from api_service.schemas import ParsingRequest, ProductOriginUpdate, ProductDependencyUpdate, ProductResponse, \
    RecalcPricesResponse, RecalcPricesRequest
from config import redis_session, settings
from engine import db

from models import Harvest, HarvestLine, ProductOrigin, ProductType, ProductBrand, ProductFeaturesGlobal, \
    ProductFeaturesLink
from models.vendor import VendorSearchLine, RewardRange
from parsing.logic import parsing_core, append_info
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
async def get_previous_results(data: ParsingRequest, redis=Depends(redis_session),
                               session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl_exists_query = select(VendorSearchLine).where(VendorSearchLine.id == data.vsl_id)
    vsl_exists_result = await session.execute(vsl_exists_query)
    if not vsl_exists_result.scalars().first():
        raise HTTPException(status_code=404, detail="Vendor_search_line с таким ID не найден")
    harvest_query = (
        select(Harvest, RewardRange)
        .join(RewardRange, Harvest.range_id == RewardRange.id)
        .where(Harvest.vendor_search_line_id == data.vsl_id)
    )
    harvest_result = await session.execute(harvest_query)
    harvest_id, reward_obj = harvest_result.first()
    if not harvest_id:
        return {"response": "not found", "is_ok": False,
                "message": "Предыдущих результатов нет, соберите данные заново"}
    harvest_line_query = (
        select(HarvestLine, ProductOrigin)
        .join(ProductOrigin, HarvestLine.origin == ProductOrigin.origin)
        .where(and_(
            HarvestLine.harvest_id == harvest_id.id,
            ProductOrigin.is_deleted.is_(False)),
        )
        .order_by(HarvestLine.input_price)
    )
    harvest_line_result = await session.execute(harvest_line_query)
    harvest_lines = harvest_line_result.all()
    result = {'is_ok': True, 'category': harvest_id.category, 'datestamp': harvest_id.datestamp,
              "range_reward": {"id": reward_obj.id, "title": reward_obj.title}}
    joined_data = list()
    for harvest_line, product_origin in harvest_lines:
        combined_dict = jsonable_encoder(harvest_line)
        combined_dict.update(jsonable_encoder(product_origin))
        joined_data.append(combined_dict)
    result['data'] = await append_info(session=session,
                                       data_lines=joined_data,
                                       redis=redis,
                                       channel=data.progress,
                                       sync_features=data.sync_features)
    await redis.publish(data.progress, "END")
    return result


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

    result_link = await session.execute(
        select(ProductFeaturesLink).where(ProductFeaturesLink.origin == data.origin)
    )
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


@parsing_router.get("/fetch_images/{origin}")
async def fetch_images_in_origin(origin: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    s3_prefix = f"{origin}/"
    result = await session.execute(
        select(ProductOrigin).where(ProductOrigin.origin == origin)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    pics = product.pics or []
    failed = []
    available_files = []

    timeout = ClientTimeout(total=10)

    s3_session = aioboto3.Session(
        aws_access_key_id=settings.s3.s3_access_key,
        aws_secret_access_key=settings.s3.s3_secret_access_key,
        region_name=settings.s3.region,
    )

    config = Config(
        signature_version=UNSIGNED,
        s3={'addressing_style': 'path'}
    )
    async with s3_session.client(
            's3',
            endpoint_url=settings.s3.s3_url,
            config=config,
            aws_access_key_id=settings.s3.s3_access_key,
            aws_secret_access_key=settings.s3.s3_secret_access_key
    ) as s3_client:
        s3_client.meta.events.register(
            'before-sign.s3.PutObject',
            lambda request, **kwargs: request.headers.update({'x-amz-content-sha256': 'UNSIGNED-PAYLOAD'})
        )
        async with ClientSession(timeout=timeout) as client_session:
            for url in pics:
                filename = os.path.basename(url.split("?")[0])
                key = f"{s3_prefix}{filename}"
                try:
                    await s3_client.head_object(Bucket=settings.s3.bucket_name, Key=key)

                    available_files.append(filename)
                    continue
                except BotoClientError as e:
                    error_code = e.response['Error'].get('Code')
                    if error_code != '404':
                        raise

                for attempt in range(1, 4):
                    try:
                        async with client_session.get(url) as response:
                            if response.status != 200:
                                raise HTTPException(status_code=response.status, detail=f"Ошибка загрузки: {url}")
                            data = await response.read()
                            await s3_client.put_object(Bucket=settings.s3.bucket_name, Key=key, Body=data)
                        available_files.append(filename)
                        break
                    except (AiohttpClientError, asyncio.TimeoutError, HTTPException) as e:
                        if attempt == 3:
                            failed.append(filename)
                        continue

    return {"origin": origin, "available": available_files, "failed_downloads": failed}


@parsing_router.post("/recalculate_output_prices", response_model=RecalcPricesResponse)
async def recalculate_reward(recalc_req: RecalcPricesRequest, redis=Depends(redis_session),
                             session: AsyncSession = Depends(db.scoped_session_dependency)):
    vsl = await session.get(VendorSearchLine, recalc_req.vsl_id)
    if not vsl:
        raise HTTPException(status_code=404, detail="VendorSearchLine не найден")

    harvest_stmt = select(Harvest).where(Harvest.vendor_search_line_id == recalc_req.vsl_id)
    harvest_res = await session.execute(harvest_stmt)
    harvest: Harvest | None = harvest_res.scalars().first()
    if not harvest:
        raise HTTPException(status_code=404, detail="Harvest не найден")

    harvest.range_id = recalc_req.range_id
    await session.flush()

    ranges = await get_range_rewards_list(session=session, range_id=recalc_req.range_id)

    hl_stmt = select(HarvestLine).where(HarvestLine.harvest_id == harvest.id)
    hl_res = await session.execute(hl_stmt)
    lines = hl_res.scalars().all()

    for line in lines:
        inp = line.input_price or 0
        line.output_price = cost_process(inp, ranges)
    await session.commit()

    join_stmt = (select(HarvestLine, ProductOrigin)
                 .join(ProductOrigin, HarvestLine.origin == ProductOrigin.origin)
                 .where(HarvestLine.harvest_id == harvest.id, ProductOrigin.is_deleted.is_(False))
                 .order_by(HarvestLine.input_price))
    result = await session.execute(join_stmt)
    rows = result.all()
    raw = list()
    for row in rows:
        line_obj = row[0]
        line_dict = dict()
        for key, val in line_obj.__dict__.items():
            if not key.startswith("_sa_"):
                line_dict[key] = val
                raw.append(line_dict)
    with_info = await append_info(session=session, data_lines=raw, redis=redis, sync_features=False)
    return {"is_ok": True, "category": harvest.category, "datestamp": harvest.datestamp,
            "range_reward": recalc_req.range_id, "data": with_info}
