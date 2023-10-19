from typing import Annotated

from fastapi import Path, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.db_support import db_support
from core.crud import get_product
from core.models import Avail


async def product_by_id(
        code: Annotated[int, Path],
        session: AsyncSession = Depends(db_support.scoped_session_dependency),
) -> Avail:
    product = await get_product(session=session, code=code)
    if product:
        return product

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product {code} not found!",
    )
