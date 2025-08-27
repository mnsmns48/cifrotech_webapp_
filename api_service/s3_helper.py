import asyncio
import aioboto3
import os

from asyncio import gather, create_task
from typing import List, Dict, Any, AsyncGenerator
from urllib.parse import urlparse
from aiobotocore.client import AioBaseClient
from aiohttp import ClientSession, ClientConnectionError, ClientResponseError, ClientTimeout
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import ParsingLinesIn
from config import settings
from models import ProductOrigin
from models.product_dependencies import ProductImage

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".svg"}


async def get_s3_client() -> AsyncGenerator[AioBaseClient, None]:
    cfg = Config(signature_version="s3v4", region_name=settings.s3.region, s3={"addressing_style": "path"})
    endpoint = settings.s3.s3_url.rstrip("/")
    session = aioboto3.Session()
    async with session.client(service_name="s3", endpoint_url=endpoint,
                              aws_access_key_id=settings.s3.s3_access_key.strip(),
                              aws_secret_access_key=settings.s3.s3_secret_access_key.strip(), config=cfg) as client:
        yield client


async def get_http_client_session():
    timeout = ClientTimeout(total=30)
    async with ClientSession(timeout=timeout) as session:
        yield session


async def build_with_preview(
        session: AsyncSession, data_lines: list[ParsingLinesIn], s3_client: AioBaseClient) -> list[ParsingLinesIn]:
    origins_to_process = set()
    origin_to_item_map = dict()

    for item in data_lines:
        origin_id = item.origin
        if origin_id and not item.preview:
            origins_to_process.add(origin_id)
            origin_to_item_map[origin_id] = item

    stmt = (select(ProductImage).where(ProductImage.origin_id.in_(origins_to_process)).order_by(
        ProductImage.origin_id.asc(), ProductImage.is_preview.desc(), ProductImage.uploaded_at.asc()))
    result = await session.execute(stmt)
    images = result.scalars().all()

    origin_to_image_map = dict()
    seen_origins = set()

    for image in images:
        origin_id = image.origin_id
        if origin_id not in seen_origins:
            origin_to_image_map[origin_id] = image
            seen_origins.add(origin_id)

    for origin_id, image in origin_to_image_map.items():
        key = image.key
        if not key:
            continue

        full_key = f"{settings.s3.s3_hub_prefix}/{origin_id}/{key}"
        try:
            preview_url = await s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": settings.s3.bucket_name, "Key": full_key},
                ExpiresIn=600
            )
        except (ClientError, BotoCoreError):
            preview_url = None

        item = origin_to_item_map.get(origin_id)
        if item:
            item["preview"] = preview_url
    return data_lines


async def scan_s3_images(s3_client, bucket: str, prefix: str) -> set[str]:
    try:
        response = await s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=100)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        raise HTTPException(403, detail=f"S3 list_objects_v2 failed: {code}")
    result = set()
    objects = response.get("Contents", [])
    for obj in objects:
        key = obj.get("Key")
        if not key:
            continue
        basename = os.path.basename(key)
        if not basename:
            continue
        title, extension = os.path.splitext(basename)
        extension = extension.lower()
        if extension in ALLOWED_EXTENSIONS:
            result.add(basename)
    return result


async def generate_presigned_for_file(s3_client, bucket: str, key: str, filename: str) -> Dict[str, str]:
    url = await s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=300
    )
    return {"filename": filename, "url": url}


async def generate_presigned_image_urls(
        filenames: set[str], prefix: str, bucket: str, s3_client) -> List[Dict[str, str]]:
    tasks = []
    for name in sorted(filenames):
        key = prefix + name
        task = create_task(generate_presigned_for_file(s3_client, bucket, key, name))
        tasks.append(task)

    return await gather(*tasks)


async def sync_images_from_pics(
        product: ProductOrigin, s3_client, cl_session: ClientSession, session: AsyncSession) -> List[Dict[str, Any]]:
    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{product.origin}/"

    try:
        existing_keys = set(await scan_s3_images(s3_client, bucket, prefix))
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Ошибка S3-сканирования: {e}")

    upload_tasks = list()
    for pic_url in product.pics or []:
        parsed = urlparse(pic_url)
        filename = os.path.basename(parsed.path.split("?", 1)[0])
        ext = os.path.splitext(filename)[1].lower()

        if pic_url.startswith("http") and ext in ALLOWED_EXTENSIONS and filename not in existing_keys:
            s3_key = f"{prefix}{filename}"

            async def _upload(url=pic_url, file_name=filename, key=s3_key):
                try:
                    async with cl_session.get(url) as resp:
                        resp.raise_for_status()
                        blob = await resp.read()
                        if not blob or len(blob) < 1024:
                            return None
                except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError):
                    return None

                try:
                    put_url = await s3_client.generate_presigned_url(
                        "put_object",
                        Params={"Bucket": bucket, "Key": key},
                        ExpiresIn=600
                    )
                    async with cl_session.put(put_url, data=blob) as put_resp:
                        if put_resp.status in (200, 201):
                            return file_name
                except (ClientError, BotoCoreError, ClientConnectionError, ClientResponseError, asyncio.TimeoutError):
                    return None

            upload_tasks.append(_upload())

    uploaded = set()
    if upload_tasks:
        results = await asyncio.gather(*upload_tasks)
        for result in results:
            if result is not None:
                uploaded.add(result)

    preview_basename = None
    preview_set = False

    if product.preview:
        preview_basename = os.path.basename(urlparse(product.preview).path)

    for img in product.pics:
        fn = os.path.basename(urlparse(img).path)
        if fn in uploaded:
            is_preview = False
            if preview_basename and not preview_set and fn == preview_basename:
                is_preview = True
                preview_set = True
            product.images.append(ProductImage(key=fn, source_url=img, is_preview=is_preview))

    session.add(product)
    await session.commit()

    keys = set()
    for img in product.images:
        if img.key:
            keys.add(img.key)
    try:
        returned_urls = await generate_presigned_image_urls(filenames=keys, prefix=prefix, bucket=bucket,
                                                            s3_client=s3_client)
    except (ClientError, BotoCoreError) as e:
        raise HTTPException(502, f"Ошибка генерации ссылок: {e}")

    return returned_urls


async def sync_images_by_origin(
        origin: int, session: AsyncSession, s3_client, cl_session: ClientSession) -> Dict[str, Any]:
    try:
        result = await session.execute(
            select(ProductOrigin).options(selectinload(ProductOrigin.images)).where(ProductOrigin.origin == origin))
        product = result.scalar_one_or_none()
    except SQLAlchemyError:
        raise HTTPException(500, "Ошибка доступа к БД")

    if not product:
        raise HTTPException(404, "Товар не найден")

    images = await sync_images_from_pics(product=product, s3_client=s3_client, cl_session=cl_session, session=session)
    url_map = dict()
    for item in images:
        filename = item.get("filename")
        url = item.get("url")
        if filename and url:
            url_map[filename] = url

    final_images = list()
    for pi in product.images:
        if pi.key and pi.key in url_map:
            final_images.append({"filename": pi.key, "url": url_map[pi.key], "is_preview": pi.is_preview})

    preview_url = product.preview
    if not preview_url:
        for img in product.images:
            if img.is_preview:
                preview_url = url_map.get(img.key)
                break
    if not preview_url and images:
        preview_url = images[0]["url"]

    return {"origin": origin, "preview": preview_url, "images": final_images}


async def generate_final_image_payload(
        product: ProductOrigin,
        s3_client,
        bucket: str,
        prefix: str
) -> dict:
    keys = []
    for img in product.images:
        keys.append(img.key)

    presigned_list = await generate_presigned_image_urls(set(keys), prefix, bucket, s3_client)

    presigned_map = {}
    for item in presigned_list:
        key = item["filename"]
        url = item["url"]
        presigned_map[key] = url

    final_images = []
    for img in product.images:
        image_data = {
            "filename": img.key,
            "url": presigned_map.get(img.key),
            "is_preview": img.is_preview
        }
        final_images.append(image_data)

    preview_url = None
    for img in product.images:
        if img.is_preview:
            key = img.key
            preview_url = presigned_map.get(key)
            break

    return {
        "images": final_images,
        "preview": preview_url
    }
