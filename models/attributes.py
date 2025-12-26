from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base, ProductType, ProductFeaturesGlobal, ProductOrigin, ProductBrand


class AttributeKey(Base):
    __tablename__ = "attribute_key"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(nullable=False, unique=True)

    attr_link: Mapped[list["AttributeLink"]] = relationship(back_populates="attr_key")
    values: Mapped[list["AttributeValue"]] = relationship(back_populates="attr_key")


class AttributeLink(Base):
    __tablename__ = "attribute_link"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_type.id", ondelete="CASCADE"), nullable=False)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("product_brand.id", ondelete="CASCADE"), nullable=True)
    attr_key_id: Mapped[int] = mapped_column(ForeignKey("attribute_key.id", ondelete="CASCADE"), nullable=False)

    product_type: Mapped["ProductType"] = relationship(back_populates="attr_link")
    brand: Mapped["ProductBrand"] = relationship(back_populates="attr_link")
    attr_key: Mapped["AttributeKey"] = relationship(back_populates="attr_link")

    __table_args__ = (UniqueConstraint("product_type_id", "brand_id", "attr_key_id", name="uq_type_brand_attr"),)


class AttributeModelOption(Base):
    __tablename__ = "attribute_model_option"

    model_id: Mapped[int] = mapped_column(ForeignKey("product_features_global.id", ondelete="CASCADE"),
                                          primary_key=True)
    attr_value_id: Mapped[int] = mapped_column(ForeignKey("attribute_value.id", ondelete="CASCADE"), primary_key=True)

    model: Mapped["ProductFeaturesGlobal"] = relationship(back_populates="attribute_options")
    attr_value: Mapped["AttributeValue"] = relationship(back_populates="model_options")


class AttributeValue(Base):
    __tablename__ = "attribute_value"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    attr_key_id: Mapped[int] = mapped_column(ForeignKey("attribute_key.id", ondelete="CASCADE"),
                                             nullable=False, index=True)
    value: Mapped[str] = mapped_column(nullable=False)
    alias: Mapped[str] = mapped_column(nullable=True)

    attr_key: Mapped["AttributeKey"] = relationship(back_populates="values")
    model_options: Mapped[list["AttributeModelOption"]] = relationship(back_populates="attr_value")
    product_values: Mapped[list["AttributeOriginValue"]] = relationship(back_populates="attr_value")

    __table_args__ = (UniqueConstraint("attr_key_id", "value", name="uq_attr_value"),)


class AttributeOriginValue(Base):
    __tablename__ = "attribute_origin_value"

    origin_id: Mapped[int] = mapped_column(ForeignKey("product_origin.origin", ondelete="CASCADE"),
                                           primary_key=True)
    attr_value_id: Mapped[int] = mapped_column(ForeignKey("attribute_value.id", ondelete="CASCADE"),
                                               primary_key=True)

    origin: Mapped["ProductOrigin"] = relationship(back_populates="attribute_values")
    attr_value: Mapped["AttributeValue"] = relationship(back_populates="product_values")
