from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base


class ProductType(Base):
    __tablename__ = "product_type"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    type: Mapped[str] = mapped_column(nullable=False)
    features: Mapped[list["ProductFeaturesGlobal"]] = relationship(back_populates="type")


class ProductBrand(Base):
    __tablename__ = "product_brand"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    type: Mapped[str] = mapped_column(nullable=False)
    features: Mapped[list["ProductFeaturesGlobal"]] = relationship(back_populates="brand")


class ProductFeaturesGlobal(Base):
    __tablename__ = "product_features_global"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    title: Mapped[str] = mapped_column(nullable=False)
    type_id: Mapped[int] = mapped_column(ForeignKey("product_type.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("product_brand.id"), nullable=False)
    info: Mapped[dict | None] = mapped_column(type_=JSON)
    type: Mapped["ProductType"] = relationship(back_populates="features")
    brand: Mapped["ProductBrand"] = relationship(back_populates="features")


class ProductOrigin(Base):
    __tablename__ = "product_origin"
    origin: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(nullable=False)
    is_deleted: Mapped[bool] = mapped_column(default=False)


class ProductDependenciesFeaturesLink(Base):
    __tablename__ = "product_features_link"

    origin: Mapped[str] = mapped_column(ForeignKey("productorigin", ondelete="CASCADE"), primary_key=True)
    feature_id: Mapped[int] = mapped_column(ForeignKey("product_features_global.id", ondelete="CASCADE"),
                                            primary_key=True)
