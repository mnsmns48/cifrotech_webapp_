import asyncio
import os
from asyncio import gather, create_task
from typing import List, Dict, Iterable

import aioboto3
from aiohttp import ClientSession, ClientConnectionError, ClientResponseError, ClientTimeout
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from fastapi import HTTPException

from config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".svg"}


async def get_s3_client():
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


async def upload_missing_images(
        pics: List[str], existing: set[str], prefix: str, bucket: str, s3_client, cl_session: ClientSession) -> set[
    str]:
    async def upload(pic_url: str, filename: str, key: str) -> str | None:
        try:
            async with cl_session.get(pic_url) as r:
                r.raise_for_status()
                data = await r.read()
        except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError) as e:
            return None
        try:
            put_url = await s3_client.generate_presigned_url(
                "put_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=600)
            async with cl_session.put(put_url, data=data) as resp:
                if resp.status in (200, 201):
                    return filename
        except (ClientConnectionError, ClientResponseError, asyncio.TimeoutError, BotoCoreError, ClientError) as e:
            return None
        return None

    tasks = list()
    for pic_url in pics:
        filename = os.path.basename(pic_url.split("?", 1)[0])
        if filename in existing:
            continue
        key = f"{prefix}{filename}"
        tasks.append(upload(pic_url, filename, key))
    results = await gather(*tasks)
    uploaded_files = set()
    for r in results:
        if r is not None:
            uploaded_files.add(r)
    return uploaded_files


async def generate_presigned_image_urls(
        filenames: set[str], prefix: str, bucket: str, s3_client) -> List[Dict[str, str]]:
    tasks = list()
    sorted_filenames: List[str] = sorted(filenames)
    for name in sorted_filenames:
        key = prefix + name

        async def generate_presigned_for_file(filename: str, s3_key: str) -> Dict[str, str]:
            url = await s3_client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": s3_key}, ExpiresIn=3600)
            return {"filename": filename, "url": url}

        task = create_task(generate_presigned_for_file(name, key))
        tasks.append(task)
    results = await gather(*tasks)
    return results
