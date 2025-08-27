from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models import VendorSearchLine, ProductOrigin


class ParsingLine(Base):
    __tablename__ = "parsing_line"
    vsl_id: Mapped[int] = mapped_column(ForeignKey("vendor_search_line.id", ondelete="CASCADE"), primary_key=True)
    origin: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_origin.origin"), primary_key=True)
    shipment: Mapped[str] = mapped_column(nullable=True)
    warranty: Mapped[str] = mapped_column(nullable=True)
    input_price: Mapped[float] = mapped_column(nullable=True)
    output_price: Mapped[float] = mapped_column(nullable=True)
    optional: Mapped[str] = mapped_column(nullable=True)

    vendor_search_line: Mapped["VendorSearchLine"] = relationship("VendorSearchLine", back_populates="parsing_lines")
    product_origin: Mapped["ProductOrigin"] = relationship("ProductOrigin", back_populates="parsing_lines")
