import datetime
from typing import TYPE_CHECKING, List
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models import Base

if TYPE_CHECKING:
    from models import ProductOrigin


class HUbMenuLevel(Base):
    __tablename__ = "hub_menu_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    sort_order: Mapped[int] = mapped_column(default=0, index=True)
    label: Mapped[str]
    icon: Mapped[Optional[str]] = mapped_column(nullable=True)
    parent_id: Mapped[int] = mapped_column(nullable=False, index=True)
    stocks: Mapped[list["HUbStock"]] = relationship(
        "HUbStock", back_populates="menu_level",cascade="all, delete-orphan")


class HubLoading(Base):
    __tablename__ = "hub_loading"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    dt_parsed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stocks: Mapped[List["HUbStock"]] = relationship(
        "HUbStock", back_populates="hub_loading", cascade="all, delete-orphan")


class HUbStock(Base):
    __tablename__ = "hub_stock"

    loading_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hub_loading.id"), nullable=True, index=True)
    origin: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_origin.origin", ondelete="CASCADE"), primary_key=True)
    path_id: Mapped[int] = mapped_column(ForeignKey("hub_menu_levels.id"), nullable=False, index=True)
    warranty: Mapped[str] = mapped_column(nullable=True)
    output_price: Mapped[float] = mapped_column(nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    menu_level: Mapped["HUbMenuLevel"] = relationship("HUbMenuLevel", back_populates="stocks")
    product_origin: Mapped["ProductOrigin"] = relationship("ProductOrigin", back_populates="stocks")
    hub_loading: Mapped[Optional["HubLoading"]] = relationship("HubLoading", back_populates="stocks")