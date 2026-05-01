from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.modulars.product.service import ProductService
from api_service.schemas import TypeModel
from engine import db

product_router = APIRouter(tags=['Product'], prefix='/product')


@product_router.get("/fetch_product_type_list", response_model=list[TypeModel])
async def fetch_product_types(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await ProductService.get_product_types(session)
