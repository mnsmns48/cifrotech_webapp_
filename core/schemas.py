from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    code: int
    name: str


class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    quantity: int | None
    price: int | None


class Dir(ProductBase):
    model_config = ConfigDict(from_attributes=True)
