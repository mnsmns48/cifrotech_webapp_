from asyncio import TimeoutError
from typing import List, Dict

from aiohttp import ClientSession, ClientConnectionError, ClientResponseError
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.crud import fetch_all_hub_levels, is_icon_used_elsewhere, fetch_ctech_pathnames
from api_service.s3_helper import get_s3_client, get_http_client_session, generate_presigned_image_urls
from api_service.schemas import RenameRequest, HubMenuLevelSchema, HubPositionPatchOut, AddHubLevelScheme, \
    AddHubLevelOutScheme, HubPositionPatch, UpdateDeleteImageScheme, UpdatedImageScheme

from config import settings
from engine import db
from models import HUbMenuLevel

hub_router = APIRouter(tags=['Hub'])


@hub_router.get("/initial_hub_levels", response_model=List[HubMenuLevelSchema])
async def get_hub_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_all_hub_levels(session)


@hub_router.get("/initial_hub_levels_with_preview", response_model=List[HubMenuLevelSchema])
async def get_hub_levels_with_preview(session: AsyncSession = Depends(db.scoped_session_dependency),
                                      s3_client=Depends(get_s3_client)):
    levels: List[HUbMenuLevel] = await fetch_all_hub_levels(session)
    filenames = {level.icon for level in levels if level.icon}
    prefix = f"{settings.s3.s3_hub_prefix}/utils/"
    bucket = settings.s3.bucket_name

    presigned_links = await generate_presigned_image_urls(filenames, prefix, bucket, s3_client)

    link_map = {item["filename"]: item["url"] for item in presigned_links}

    for level in levels:
        if level.icon and level.icon in link_map:
            level.icon = link_map[level.icon]

    return levels


@hub_router.get("/initial_cifrotech_levels")
async def initial_cifrotech_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_ctech_pathnames(session)


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


@hub_router.post("/loading_hub_one_image")
async def upload_image_to_origin(code: int = Form(...),
                                 file: UploadFile = File(...),
                                 session: AsyncSession = Depends(db.scoped_session_dependency),
                                 s3_client=Depends(get_s3_client),
                                 cl_session: ClientSession = Depends(get_http_client_session)):
    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{settings.s3.utils_path}/"
    new_key = f"{prefix}{file.filename}"

    result = await session.execute(select(HUbMenuLevel).where(HUbMenuLevel.id == code))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(404, detail="Уровень не найден")

    old_filename = item.icon

    try:
        put_url = await s3_client.generate_presigned_url(
            ClientMethod="put_object", Params={"Bucket": bucket, "Key": new_key}, ExpiresIn=600)
        body = await file.read()
    except Exception as e:
        raise HTTPException(400, f"Не удалось подготовить загрузку: {e}")

    try:
        async with cl_session.put(put_url, data=body) as resp:
            resp.raise_for_status()
    except (ClientConnectionError, ClientResponseError, TimeoutError) as e:
        raise HTTPException(502, f"Ошибка загрузки в S3: {e}")

    item.icon = file.filename
    await session.commit()

    if old_filename and old_filename != file.filename:
        check_result = await session.execute(
            select(HUbMenuLevel).where(HUbMenuLevel.icon == old_filename)
        )
        still_used = check_result.scalars().first()
        if not still_used:
            old_key = f"{prefix}{old_filename}"
            try:
                await s3_client.delete_object(Bucket=bucket, Key=old_key)
            except Exception as e:
                raise HTTPException(500, f"Не удалось удалить старый файл: {e}")

    try:
        presigned_list: List[Dict[str, str]] = await generate_presigned_image_urls({file.filename}, prefix, bucket,
                                                                                   s3_client)
        presigned_url = presigned_list[0]["url"]
    except Exception as e:
        raise HTTPException(500, f"Не удалось сгенерировать ссылку: {e}")

    return {"id": code, 'filename': file.filename, 'url': presigned_url}


@hub_router.post("/update_or_delete_image", response_model=UpdatedImageScheme)
async def update_or_delete_image(payload: UpdateDeleteImageScheme,
                                 session: AsyncSession = Depends(db.scoped_session_dependency),
                                 s3_client=Depends(get_s3_client)):
    bucket = settings.s3.bucket_name
    prefix = f"{settings.s3.s3_hub_prefix}/{settings.s3.utils_path}/"

    stmt = select(HUbMenuLevel).where(HUbMenuLevel.id == payload.code)
    result = await session.execute(stmt)
    menu_level = result.scalar_one_or_none()

    if not menu_level:
        raise HTTPException(status_code=404, detail="Категория меню не найдена")

    current_icon = menu_level.icon
    new_icon = payload.icon
    presigned_url = None

    if new_icon is None:
        if current_icon:
            if not await is_icon_used_elsewhere(current_icon, menu_level.id, session):
                await s3_client.delete_object(Bucket=bucket, Key=f"{prefix}{current_icon}")
            menu_level.icon = None
            await session.commit()

    else:
        try:
            await s3_client.head_object(Bucket=bucket, Key=f"{prefix}{new_icon}")
            old_icon = current_icon
            menu_level.icon = new_icon
            await session.commit()

            presigned_list = await generate_presigned_image_urls({new_icon}, prefix, bucket, s3_client)
            presigned_url = presigned_list[0]["url"]

            if old_icon and old_icon != new_icon:
                if not await is_icon_used_elsewhere(old_icon, menu_level.id, session):
                    await s3_client.delete_object(Bucket=bucket, Key=f"{prefix}{old_icon}")

        except s3_client.exceptions.ClientError:
            return UpdatedImageScheme(code=menu_level.id, icon=current_icon or "", url=None)

    return UpdatedImageScheme(code=menu_level.id, icon=menu_level.icon, url=presigned_url)
