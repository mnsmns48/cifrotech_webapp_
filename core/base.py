from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.settings import settings


class DBSupport:
    def __init__(self, url: str, echo: bool = False):
        self.engine = create_async_engine(url=url, echo=echo)
        self.session_factory = async_sessionmaker(
            bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False
        )


db_support = DBSupport(url=settings.db_url, echo=settings.db_echo)


class Base(DeclarativeBase):
    code: Mapped[int] = mapped_column(primary_key=True)


class Directory(Base):
    __tablename__ = "avail"
    type_: Mapped[str]
    brand: Mapped[str]
    code: Mapped[int]
    product: Mapped[str]
    quantity: Mapped[int]
    price: Mapped[int]
