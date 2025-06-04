from typing import List

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.annotation import Annotated

from models.base import Base


class Vendor(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(nullable=False, primary_key=False)
    source: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[str] = mapped_column(nullable=True)
    login: Mapped[str] = mapped_column(nullable=True)
    password: Mapped[str] = mapped_column(nullable=True)
    function: Mapped[str] = mapped_column(nullable=True)
    search_lines: Mapped[list["Vendor_search_line"]] = relationship("Vendor_search_line", back_populates="vendor",
                                                                    cascade="all, delete")


class Vendor_search_line(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="search_lines")


class Harvest(Base):
    origin: Mapped[str] = mapped_column(primary_key=True, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    link: Mapped[str] = mapped_column(nullable=True)
    shipment: Mapped[str] = mapped_column(nullable=True)
    warranty: Mapped[str] = mapped_column(nullable=True)
    input_price: Mapped[float] = mapped_column(nullable=True)
    output_price: Mapped[float] = mapped_column(nullable=True)
    pics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    preview: Mapped[str] = mapped_column(nullable=True)
    optional: Mapped[str] = mapped_column(nullable=True)


class RewardRange(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, )
    title: Mapped[str] = mapped_column(nullable=False)
    is_default: Mapped[bool] = mapped_column(nullable=False)
    lines: Mapped[list["RewardRangeLine"]] = relationship("RewardRangeLine",
                                                          back_populates="range", cascade="all, delete")


class RewardRangeLine(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    range_id: Mapped[int] = mapped_column(ForeignKey("rewardrange.id", ondelete="CASCADE"), nullable=False)
    line_from: Mapped[int] = mapped_column(nullable=False)
    line_to: Mapped[int] = mapped_column(nullable=False)
    is_percent: Mapped[bool] = mapped_column(nullable=False)
    reward: Mapped[int] = mapped_column(nullable=False)
    range: Mapped["RewardRange"] = relationship("RewardRange", back_populates="lines")

# class OrderCatalog(Base):
#     origin: Mapped[int] = mapped_column(primary_key=True, unique=True, nullable=False)
#     title: Mapped[str] = mapped_column(nullable=False)
#     shipment: Mapped[str] = mapped_column(nullable=True)
#     warranty: Mapped[str] = mapped_column(nullable=True)
#     input_price: Mapped[float] = mapped_column(nullable=True)
#     output_price: Mapped[float] = mapped_column(nullable=True)
#     pic: Mapped[str] = mapped_column(nullable=True)
#     optional: Mapped[str] = mapped_column(nullable=True)
