from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependence import product_by_code
from core.engine import pg_engine
from core.crud import get_directory

from core.schemas import Product, Dir

dir_router = APIRouter()


@dir_router.get("/all", response_model=list[Dir])
async def get_main(session: AsyncSession = Depends(pg_engine.session_dependency)):
    return await get_directory(session=session, parent=0)


@dir_router.get("/{dirs}", response_model=list[Dir])
async def get_dirs(
    parent: int, session: AsyncSession = Depends(pg_engine.session_dependency)
):
    return await get_directory(session=session, parent=parent)


@dir_router.get("/stock/{code}", response_model=Product)
async def get_product_by_code(product: Product = Depends(product_by_code)):
    return product
