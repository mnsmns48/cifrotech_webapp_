from sqlalchemy import BigInteger, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class Activity(Base):
    operation_code: Mapped[int] = mapped_column(primary_key=True)
    time_: Mapped[str] = mapped_column(TIMESTAMP)
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
    fullname: Mapped[str | None]
    username: Mapped[str | None]


class TgBotOptions(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    username: Mapped[str] = mapped_column(primary_key=True)
    main_pic: Mapped[str | None]
