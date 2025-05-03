from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Vendor(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[str] = mapped_column(nullable=True)