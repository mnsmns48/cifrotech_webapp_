from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import ServiceImageResponse, ServiceImageCreate, ServiceImageUpdate
from app_utils import get_url_from_s3
from api_service.crud import fetch_utils_images, check_service_image
from config import settings
from engine import db
from models import ServiceImage

utils_router = APIRouter(tags=['Service-Utils'])


@utils_router.get('/get_utils_images', response_model=List[ServiceImageResponse])
async def get_utils_images(session: AsyncSession = Depends(db.scoped_session_dependency)):
    fetch = await fetch_utils_images(session)
    if not fetch:
        return []

    response = list()
    for item in fetch:
        response.append(
            ServiceImageResponse(
                id=item.id,
                var=item.var,
                value=item.value,
                image=get_url_from_s3(filename=item.value, path=settings.s3.utils_path)
            )
        )
    return response


@utils_router.post("/update_service_image", response_model=ServiceImageResponse)
async def create_service_image_endpoint(payload: ServiceImageCreate,
                                        session: AsyncSession = Depends(db.scoped_session_dependency)):
    existing = await check_service_image(session, ServiceImage.var, payload.var, raise_if_not_found=False)
    if existing:
        raise HTTPException(status_code=400, detail=f"ServiceImage with var '{payload.var}' already exists")

    new_item = ServiceImage(var=payload.var, value=payload.value)
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)

    return ServiceImageResponse(id=new_item.id, var=new_item.var,
                                value=new_item.value,
                                image=get_url_from_s3(filename=new_item.value, path=settings.s3.utils_path))


@utils_router.put("/update_service_image/{item_id}", response_model=ServiceImageResponse)
async def update_service_image_endpoint(item_id: int, payload: ServiceImageUpdate,
                                        session: AsyncSession = Depends(db.scoped_session_dependency)):
    item = await check_service_image(session, ServiceImage.id, item_id)
    if payload.var is not None:
        item.var = payload.var
    if payload.value is not None:
        item.value = payload.value

    session.add(item)
    await session.commit()
    await session.refresh(item)

    return ServiceImageResponse(id=item.id, var=item.var, value=item.value,
                                image=get_url_from_s3(filename=item.value, path=settings.s3.utils_path))


@utils_router.delete("/update_service_image/{item_id}")
async def delete_service_image_endpoint(item_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    item = await check_service_image(session, ServiceImage.id, item_id)
    await session.delete(item)
    await session.commit()
    return {'response': True}
