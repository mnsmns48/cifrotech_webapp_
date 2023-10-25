from typing import Annotated

from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.crud import get_product
from core.engine import pg_engine
from core.models import StockTable


async def product_by_code(
        code: Annotated[int, Path],
        session: AsyncSession = Depends(pg_engine.scoped_session_dependency)) -> StockTable:
    product = await get_product(session=session, code=code)
    if product:
        return product

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product {code} not found!",
    )
