from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api_service.schemas import BrandModel, BrandsBulkList
from models import ProductType, ProductBrand


class ProductService:
    @staticmethod
    async def get_product_types(session) -> list[ProductType]:
        result = await session.execute(select(ProductType))
        return result.scalars().all()

    @staticmethod
    async def get_brands(session) -> list[BrandModel]:
        result = await session.execute(select(ProductBrand))
        return result.scalars().all()

    @staticmethod
    async def update_brands(brands_bulk: BrandsBulkList, session) -> list[str]:
        incoming = {b.strip().lower() for b in brands_bulk.brands if b.strip()}
        if not incoming:
            return []
        existing_rows = await session.execute(
            select(ProductBrand.brand).where(ProductBrand.brand.in_(incoming))
        )
        existing = {row[0] for row in existing_rows}
        to_insert = incoming - existing
        added = list()
        for brand in to_insert:
            obj = ProductBrand(brand=brand)
            session.add(obj)
            added.append(brand)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        return added
