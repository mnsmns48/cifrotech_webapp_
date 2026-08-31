from typing import Dict, List, Callable, Type, Any

from aiohttp import ClientSession, ClientConnectionError, ClientResponseError, ClientError
from fastapi import UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud.main import is_icon_used_elsewhere
from api_service.s3_helper import generate_presigned_image_urls
from api_service.schemas import UpdatedImageScheme
from cache.manager import T


async def process_image_upload(code: int, file: UploadFile,
                               s3_client, cl_session: ClientSession,
                               session: AsyncSession, bucket: str, prefix: str,
                               get_item_func: Callable, update_db_icon_func: Callable):
    new_key = f"{prefix}{file.filename}"
    item = await get_item_func(session, code)
    if not item:
        raise HTTPException(404, detail="Категория/папка не найдена")

    try:
        put_url = await s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": bucket, "Key": new_key, "ACL": "public-read"},
            ExpiresIn=600,
        )
        body = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Не удалось подготовить загрузку: {e}")

    try:
        async with cl_session.put(put_url, data=body, headers={"x-amz-acl": "public-read"}) as resp:
            resp.raise_for_status()
    except (ClientConnectionError, ClientResponseError, TimeoutError, ClientError) as e:
        raise HTTPException(502, f"Ошибка загрузки в S3: {e}")

    old_filename = await update_db_icon_func(session, code, file.filename)

    if old_filename and old_filename != file.filename:
        still_used = await is_icon_used_elsewhere(old_filename, exclude_id=code, session=session)
        if not still_used:
            try:
                await s3_client.delete_object(Bucket=bucket, Key=f"{prefix}{old_filename}")
            except Exception as e:
                raise HTTPException(500, f"Не удалось удалить старый файл: {e}")

    try:
        presigned_list: List[Dict[str, str]] = await generate_presigned_image_urls(
            {file.filename}, prefix, bucket, s3_client)
        presigned_url = presigned_list[0]["url"]
    except Exception as e:
        raise HTTPException(500, f"Не удалось сгенерировать ссылку: {e}")

    return {"id": code, "filename": file.filename, "url": presigned_url}


async def process_image_update(code: int, current_icon: str | None, new_icon: str | None,
                               s3_client, session: AsyncSession, bucket: str, prefix: str,
                               update_db_icon: Callable) -> UpdatedImageScheme:
    if new_icon is None:
        if current_icon:
            if not await is_icon_used_elsewhere(current_icon, code, session):
                await s3_client.delete_object(Bucket=bucket, Key=f"{prefix}{current_icon}")
            await update_db_icon(None)
        return UpdatedImageScheme(code=code, icon=None, url=None)

    try:
        await s3_client.head_object(Bucket=bucket, Key=f"{prefix}{new_icon}")
        old_icon = current_icon
        await update_db_icon(new_icon)

        presigned_list = await generate_presigned_image_urls({new_icon}, prefix, bucket, s3_client)
        presigned_url = presigned_list[0]["url"]

        if old_icon and old_icon != new_icon:
            if not await is_icon_used_elsewhere(old_icon, code, session):
                await s3_client.delete_object(Bucket=bucket, Key=f"{prefix}{old_icon}")

    except s3_client.exceptions.ClientError:
        return UpdatedImageScheme(code=code, icon=current_icon or "", url=None)

    return UpdatedImageScheme(code=code, icon=new_icon, url=presigned_url)


def collect_unique_models(items: list[Any], attr_name: str, model: Type[T]) -> list[T]:
    seen: dict[int, T] = dict()

    for item in items:
        obj = getattr(item, attr_name, None)
        if obj is None:
            continue

        obj_id = getattr(obj, "id", None)
        if obj_id is None:
            continue

        if obj_id not in seen:
            seen[obj_id] = model.model_validate(obj)

    return list(seen.values())
