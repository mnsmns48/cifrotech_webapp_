from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models import HUbStock, HarvestLine


class Vendor(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(nullable=False, primary_key=False)
    source: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[str] = mapped_column(nullable=True)
    login: Mapped[str] = mapped_column(nullable=True)
    password: Mapped[str] = mapped_column(nullable=True)
    function: Mapped[str] = mapped_column(nullable=True)
    search_lines: Mapped[list["VendorSearchLine"]] = relationship("VendorSearchLine", back_populates="vendor",
                                                                  cascade="all, delete")


class VendorSearchLine(Base):
    __tablename__ = "vendor_search_line"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    dt_parsed: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=True)
    profit_range_id: Mapped[int] = mapped_column(ForeignKey("rewardrange.id", ondelete="SET NULL"), nullable=True)

    harvest_lines: Mapped["HarvestLine"] = relationship("HarvestLine", back_populates="vendor_search_line")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="search_lines")
    stocks: Mapped["HUbStock"] = relationship("HUbStock", back_populates="search_lines")


class RewardRange(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, )
    title: Mapped[str] = mapped_column(nullable=False)
    is_default: Mapped[bool] = mapped_column(nullable=False)
    lines: Mapped[list["RewardRangeLine"]] = relationship("RewardRangeLine",
                                                          back_populates="range", cascade="all, delete")


class RewardRangeLine(Base):
    __tablename__ = "reward_range_line"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    range_id: Mapped[int] = mapped_column(ForeignKey("rewardrange.id", ondelete="CASCADE"), nullable=False)
    line_from: Mapped[int] = mapped_column(nullable=False)
    line_to: Mapped[int] = mapped_column(nullable=False)
    is_percent: Mapped[bool] = mapped_column(nullable=False)
    reward: Mapped[int] = mapped_column(nullable=False)
    range: Mapped["RewardRange"] = relationship("RewardRange", back_populates="lines")
