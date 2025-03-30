from datetime import datetime

from sqlalchemy import BigInteger, func, Computed, DateTime, Index, text, event
from sqlalchemy.dialects.postgresql import JSON, TIMESTAMP, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


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


class TgBotOptions(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    username: Mapped[str] = mapped_column(primary_key=True)
    main_pic: Mapped[str] = mapped_column(nullable=True)


class Sellers(Base):
    seller: Mapped[str | None]
    time_: Mapped[TIMESTAMP] = mapped_column(TIMESTAMP(timezone=False), primary_key=True)
    product_type: Mapped[str] = mapped_column(nullable=True)
    brand: Mapped[str] = mapped_column(nullable=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    price_1: Mapped[str] = mapped_column(nullable=True)
    price_2: Mapped[str] = mapped_column(nullable=True)


class Vendor(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[str] = mapped_column(nullable=True)


class Products(Base):
    __table_args__ = (
        Index('idx_title_tsv', 'title_tsv', postgresql_using='gin'),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    title: Mapped[str]
    title_tsv: Mapped[TSVECTOR] = mapped_column(TSVECTOR, Computed("to_tsvector('simple', title)", persisted=True))


class ProductInfo(Base):
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int]
    info: Mapped[dict] = mapped_column(type_=JSON, nullable=True)


class VendorStock(Base):
    vendor_code: Mapped[int] = mapped_column(nullable=True)
    vendor_id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(primary_key=True)
    vendor_price: Mapped[float]
    client_price: Mapped[float]
    delivery_term: Mapped[str] = mapped_column(nullable=True)
    source_data: Mapped[str] = mapped_column(nullable=True)
    create: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    update: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())


@event.listens_for(Products.__table__, 'after_create')
def create_update_title_tsv_trigger(target, connection, **kw):
    connection.execute(text(
        f"""
        CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
        ON {Products.__table__} FOR EACH ROW EXECUTE PROCEDURE
        tsvector_update_trigger(title_tsv, 'pg_catalog.simple', title);
        """
    ))
