from aiohttp import ClientSession
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.api_connect import update_product_from_dtube
from api_service.modulars.product.service import ProductService
from api_service.s3_helper import get_http_client_session
from api_service.schemas import TypeModel, UpdateProductFromDTPayload, BrandModel, BrandsBulkList
from engine import db
from models import ProductFeaturesGlobal

product_router = APIRouter(tags=['Product'], prefix='/product')


@product_router.get("/fetch_product_type_list", response_model=list[TypeModel])
async def fetch_product_types(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await ProductService.get_product_types(session)


@product_router.get("/fetch_brands_list", response_model=list[BrandModel])
async def fetch_brands(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await ProductService.get_brands(session)


@product_router.post("/update_product_from_dt")
async def update_product_from_dt(payload: UpdateProductFromDTPayload,
                                 cl_session: ClientSession = Depends(get_http_client_session),
                                 session: AsyncSession = Depends(db.scoped_session_dependency)):
    dtube_data = await update_product_from_dtube(payload, cl_session)

    if not dtube_data:
        raise HTTPException(404, "DigitalTube returned empty result")

    stmt = select(ProductFeaturesGlobal).where(ProductFeaturesGlobal.title == payload.title)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(404, "Product not found in local DB")

    product.info = dtube_data.get("info")
    product.pros_cons = dtube_data.get("pros_cons")

    await session.commit()
    await session.refresh(product)

    return {"updated": True,
            "id": product.id,
            "title": product.title,
            "info": product.info,
            "pros_cons": product.pros_cons}


@product_router.post("/update_brands")
async def update_brands(brands_bulk: BrandsBulkList, session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await ProductService.update_brands(brands_bulk, session)
