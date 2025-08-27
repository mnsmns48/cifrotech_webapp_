from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, BigInteger, Index, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base
from datetime import datetime

if TYPE_CHECKING:
    from .parsing import ParsingLine
    from .hub import HUbStock


class ProductType(Base):
    __tablename__ = "product_type"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    type: Mapped[str] = mapped_column(nullable=False, unique=True)
    features: Mapped[list["ProductFeaturesGlobal"]] = relationship(back_populates="type")


class ProductBrand(Base):
    __tablename__ = "product_brand"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    brand: Mapped[str] = mapped_column(nullable=False, unique=True)
    features: Mapped[list["ProductFeaturesGlobal"]] = relationship(back_populates="brand")


class ProductFeaturesGlobal(Base):
    __tablename__ = "product_features_global"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    title: Mapped[str] = mapped_column(nullable=False, unique=True)
    type_id: Mapped[int] = mapped_column(ForeignKey("product_type.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("product_brand.id"), nullable=False)
    info: Mapped[dict | None] = mapped_column(JSONB)
    pros_cons: Mapped[dict | None] = mapped_column(JSONB)
    type: Mapped["ProductType"] = relationship(back_populates="features")
    brand: Mapped["ProductBrand"] = relationship(back_populates="features")


class ProductOrigin(Base):
    __tablename__ = "product_origin"
    origin: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    link: Mapped[str] = mapped_column(nullable=True)
    pics: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=True)
    preview: Mapped[str] = mapped_column(nullable=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)

    images: Mapped[list["ProductImage"]] = relationship(back_populates="origin", cascade="all, delete-orphan")
    parsing_lines: Mapped[list["ParsingLine"]] = relationship("ParsingLine", back_populates="product_origin")
    stocks: Mapped[list[HUbStock]] = relationship(
        "HUbStock", back_populates="product_origin", cascade="all, delete-orphan")


class ProductImage(Base):
    __tablename__ = "product_image"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    origin_id: Mapped[int] = mapped_column(ForeignKey("product_origin.origin", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(nullable=False)
    source_url: Mapped[str | None] = mapped_column(nullable=True)
    is_preview: Mapped[bool] = mapped_column(default=False)
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())
    checksum: Mapped[str | None] = mapped_column(nullable=True)

    origin: Mapped["ProductOrigin"] = relationship(back_populates="images")


class ProductFeaturesLink(Base):
    __tablename__ = "product_features_link"
    origin: Mapped[int] = mapped_column(BigInteger,
                                        ForeignKey("product_origin.origin", ondelete="CASCADE"),
                                        primary_key=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey("product_features_global.id", ondelete="CASCADE"),
                                            primary_key=True)
    __table_args__ = (Index("ix_pf_link_feature", "feature_id"),)
