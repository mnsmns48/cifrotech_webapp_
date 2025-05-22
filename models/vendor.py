from datetime import datetime

from sqlalchemy import ForeignKey, DATETIME, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
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
    harvests: Mapped[list["Harvest"]] = relationship("Harvest", back_populates="vendor",
                                                     cascade="all, delete")


class Vendor_search_line(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="search_lines")


class Harvest(Base):
    date: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    origin: Mapped[int] = mapped_column(primary_key=True, unique=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    shipment: Mapped[str] = mapped_column(nullable=True)
    warranty: Mapped[str] = mapped_column(nullable=True)
    input_price: Mapped[float] = mapped_column(nullable=True)
    pic: Mapped[str] = mapped_column(nullable=True)
    optional: Mapped[str] = mapped_column(nullable=True)
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="harvests")
