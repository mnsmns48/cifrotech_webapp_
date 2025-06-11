from sqlalchemy import ForeignKey, String, DateTime, func, JSON
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Harvest(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    vendor_search_line_id: Mapped[int] = mapped_column(ForeignKey("vendor_search_line.id"), nullable=False)
    datestamp: Mapped[DateTime] = mapped_column(DateTime(timezone=True), default=func.now())
    category: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    vendor_search_line: Mapped["VendorSearchLine"] = relationship("VendorSearchLine", back_populates="harvests")
    harvest_lines: Mapped[list["HarvestLine"]] = relationship("HarvestLine", back_populates="harvest",
                                                              cascade="all, delete")


class HarvestLine(Base):
    __tablename__ = "harvest_line"
    harvest_id: Mapped[int] = mapped_column(ForeignKey("harvest.id", ondelete="CASCADE"), nullable=False)
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
    harvest: Mapped["Harvest"] = relationship("Harvest", back_populates="harvest_lines")


class DetailDependencies(Base):
    __tablename__ = "detail_dependencies"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    origin: Mapped[str] = mapped_column(unique=True, nullable=False)
    info: Mapped[dict | None] = mapped_column(type_=JSON)


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
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="search_lines")
    harvests: Mapped[list["Harvest"]] = relationship("Harvest", back_populates="vendor_search_line",
                                                     cascade="all, delete")


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
