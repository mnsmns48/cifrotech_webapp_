from sqlalchemy import select

from api_service.schemas import BrandModel
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
