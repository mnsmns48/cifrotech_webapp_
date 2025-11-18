from typing import List

from fastapi import APIRouter, Depends
from fastapi_cache.decorator import cache
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api_miniapp.crud import fetch_hub_levels
from api_miniapp.schemas import HubLevelScheme
from api_miniapp.schemas.hub_prod_scheme import HubProductScheme
from engine import db
from models import HUbStock, ProductOrigin, ProductImage

hub_product = APIRouter()


@hub_product.get("/hub_levels", response_model=List[HubLevelScheme])
@cache(expire=10)
async def get_levels(session: AsyncSession = Depends(db.scoped_session_dependency)):
    return await fetch_hub_levels(session)


@hub_product.post("/get_products_by_path", response_model=List[HubProductScheme])
async def get_products_by_parent(path_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    from sqlalchemy import select, and_, func
    from sqlalchemy.orm import aliased

    Image = aliased(ProductImage)
    PreviewImage = aliased(ProductImage)

    stmt = (
        select(
            HUbStock.id,
            HUbStock.origin,
            HUbStock.warranty,
            HUbStock.output_price,
            ProductOrigin.title,

            func.array_agg(Image.key).filter(Image.key.isnot(None)).label("pics"),

            PreviewImage.key.label("preview"),
        )
        .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)

        # все картинки
        .outerjoin(ProductImage, ProductImage.origin_id == ProductOrigin.origin)

        # только preview-картинка
        .outerjoin(
            PreviewImage,
            and_(
                PreviewImage.origin_id == ProductOrigin.origin,
                PreviewImage.is_preview == True
            )
        )
        .where(
            HUbStock.path_id == path_id,
            ProductOrigin.is_deleted == False
        )
        .group_by(
            HUbStock.id,
            ProductOrigin.title,
            PreviewImage.key
        )
    )

    execute = await session.execute(stmt)
    rows = execute.mappings().all()
    result = list()

    for row in rows:
        result.append(HubProductScheme.model_validate(row))

    return result
