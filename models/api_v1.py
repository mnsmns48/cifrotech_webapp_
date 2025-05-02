from sqlalchemy import func, BigInteger
from sqlalchemy.dialects.postgresql import TIMESTAMP, JSON
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Activity(Base):
    operation_code: Mapped[int] = mapped_column(primary_key=True)
    time_: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP)
    product_code: Mapped[int]
    product: Mapped[str]
    quantity: Mapped[int]
    price: Mapped[float]
    sum_: Mapped[float]
    noncash: Mapped[bool]
    return_: Mapped[bool]


class StockTable(Base):
    code: Mapped[int] = mapped_column(primary_key=True)
    parent: Mapped[int]
    ispath: Mapped[bool]
    name: Mapped[str]
    quantity: Mapped[int] = mapped_column(nullable=True)
    price: Mapped[int] = mapped_column(nullable=True)
    info: Mapped[dict | None] = mapped_column(type_=JSON)


class Guests(Base):
    time_: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP(timezone=False), server_default=func.now())
    id_: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    fullname: Mapped[str] = mapped_column(nullable=True)
    username: Mapped[str] = mapped_column(nullable=True)


class Sellers(Base):
    seller: Mapped[str | None]
    time_: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP(timezone=False), primary_key=True)
    product_type: Mapped[str] = mapped_column(nullable=True)
    brand: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    price_1: Mapped[str] = mapped_column(nullable=True)
    price_2: Mapped[str] = mapped_column(nullable=True)