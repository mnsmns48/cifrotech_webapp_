from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime, func, String, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from models.vendor import VendorSearchLine

if TYPE_CHECKING:
    from .vendor import VendorSearchLine
    from .product_dependencies import ProductOrigin


class Harvest(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    vendor_search_line_id: Mapped[int] = mapped_column(ForeignKey("vendor_search_line.id"), nullable=False)
    range_id: Mapped[int] = mapped_column(ForeignKey("rewardrange.id", ondelete="SET NULL"), nullable=True)
    datestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now())
    category: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    vendor_search_line: Mapped["VendorSearchLine"] = relationship("VendorSearchLine", back_populates="harvests")
    harvest_lines: Mapped[list["HarvestLine"]] = relationship("HarvestLine", back_populates="harvest",
                                                              cascade="all, delete")


class HarvestLine(Base):
    __tablename__ = "harvest_line"
    harvest_id: Mapped[int] = mapped_column(ForeignKey("harvest.id", ondelete="CASCADE"), primary_key=True)
    origin: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_origin.origin"), primary_key=True)
    shipment: Mapped[str] = mapped_column(nullable=True)
    warranty: Mapped[str] = mapped_column(nullable=True)
    input_price: Mapped[float] = mapped_column(nullable=True)
    output_price: Mapped[float] = mapped_column(nullable=True)
    optional: Mapped[str] = mapped_column(nullable=True)
    harvest: Mapped["Harvest"] = relationship("Harvest", back_populates="harvest_lines")
    product_origin: Mapped["ProductOrigin"] = relationship("ProductOrigin", back_populates="harvest_lines")
