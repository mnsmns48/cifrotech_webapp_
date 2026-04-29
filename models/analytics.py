from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models import AttributeValue


class ProductTypeWeightRule(Base):
    __tablename__ = "product_type_weight_rule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_type_id: Mapped[int] = mapped_column(ForeignKey("product_type.id"), nullable=False, index=True)
    attr_key_id: Mapped[int] = mapped_column(ForeignKey("attribute_key.id"), nullable=False, index=True)
    weight: Mapped[float]
    description: Mapped[Optional[str]]
    is_enabled: Mapped[bool] = mapped_column(nullable=False, default=True)

    product_type = relationship("ProductType", back_populates="weight_rules")
    attr_key = relationship("AttributeKey", back_populates="weight_rules")
    value_maps = relationship("ProductTypeValueMap", back_populates="rule", cascade="all, delete-orphan")


class ProductTypeValueMap(Base):
    __tablename__ = "product_type_value_map"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("product_type_weight_rule.id", ondelete="CASCADE"),
                                         nullable=False, index=True)
    attr_value_id: Mapped[int] = mapped_column(ForeignKey("attribute_value.id", ondelete="CASCADE"),
                                               nullable=False, index=True)
    multiplier: Mapped[float] = mapped_column(Float, nullable=False)

    rule: Mapped["ProductTypeWeightRule"] = relationship(back_populates="value_maps")
    attr_value: Mapped["AttributeValue"] = relationship(back_populates="value_maps")
