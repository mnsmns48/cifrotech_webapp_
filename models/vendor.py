from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class Vendor(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    name: Mapped[str] = mapped_column(nullable=False, primary_key=False)
    source: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[str] = mapped_column(nullable=True)
    search_lines: Mapped[list["Vendor_search_line"]] = relationship("Vendor_search_line", back_populates="vendor",
                                                                    cascade="all, delete")


class Vendor_search_line(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=False)
    vendor: Mapped["Vendor"] = relationship("Vendor", back_populates="search_lines")
