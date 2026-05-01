from sqlalchemy import select

from models import ProductType


class ProductService:
    @staticmethod
    async def get_product_types(session) -> list[ProductType]:
        result = await session.execute(select(ProductType))
        return result.scalars().all()
