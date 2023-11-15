from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    name: str


class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    code: int
    quantity: int | None
    price: int | None
    desc: str | None


# class Dir(ProductBase):
#     model_config = ConfigDict(from_attributes=True)
