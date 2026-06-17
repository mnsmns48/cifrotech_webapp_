from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from .hub import HUbStock
    from .parsing import ParsingLine


class Vendor(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(nullable=False, primary_key=False)
    source: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[str] = mapped_column(nullable=True)
    login: Mapped[str] = mapped_column(nullable=True)
    password: Mapped[str] = mapped_column(nullable=True)
    function: Mapped[str] = mapped_column(nullable=True)
    token_id: Mapped[int | None] = mapped_column(ForeignKey("vendor_api_token.id"), nullable=True)
    search_lines: Mapped[list["VendorSearchLine"]] = relationship("VendorSearchLine", back_populates="vendor",
                                                                  cascade="all, delete")
    api_token: Mapped["VendorApiToken"] = relationship("VendorApiToken", back_populates="vendor", lazy="selectin")


class VendorApiToken(Base):
    __tablename__ = "vendor_api_token"

    id: Mapped[int] = mapped_column(primary_key=True)

    access_token: Mapped[str | None] = mapped_column(nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(nullable=True)
    token_type: Mapped[str] = mapped_column(nullable=False, default="Bearer")

    access_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_auth_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)

    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="api_token")


class VendorSearchLine(Base):
    __tablename__ = "vendor_search_line"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    dt_parsed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    parsing_lines: Mapped["ParsingLine"] = relationship("ParsingLine", back_populates="vendor_search_line")
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="search_lines")
    stocks: Mapped["HUbStock"] = relationship("HUbStock", back_populates="search_lines")


class RewardRange(Base):
    __tablename__ = "rewardrange"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, )
    title: Mapped[str] = mapped_column(nullable=False)
    is_default: Mapped[bool] = mapped_column(nullable=False)
    lines: Mapped[list["RewardRangeLine"]] = relationship("RewardRangeLine",
                                                          back_populates="range", cascade="all, delete")

    parsing_lines: Mapped[list["ParsingLine"]] = relationship("ParsingLine", back_populates="reward_range")
    stocks: Mapped[list["HUbStock"]] = relationship("HUbStock", back_populates="reward_range")


class RewardRangeLine(Base):
    __tablename__ = "reward_range_line"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    range_id: Mapped[int] = mapped_column(ForeignKey("rewardrange.id", ondelete="CASCADE"), nullable=False)
    line_from: Mapped[int] = mapped_column(nullable=False)
    line_to: Mapped[int] = mapped_column(nullable=False)
    is_percent: Mapped[bool] = mapped_column(nullable=False)
    reward: Mapped[int] = mapped_column(nullable=False)
    range: Mapped["RewardRange"] = relationship("RewardRange", back_populates="lines")
