from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_support import db_support
from core.crud import get_directory
from core.dependence import product_by_id

from core.models import Avail

router = APIRouter()


@router.get("/dirs")
async def get_dirs(session: AsyncSession = Depends(db_support.session_dependency)):
    return await get_directory(session=session)


@router.get("/{code}")
async def get_product_by_code(product: Avail = Depends(product_by_id)):
    return product
