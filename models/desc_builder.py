from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, Boolean
from sqlalchemy.orm import mapped_column, relationship, Mapped

from models import Base

if TYPE_CHECKING:
    from models import ProductType, ProductBrand, FormulaExpression, FormulaEntityType


class DescBuilder(Base):
    __tablename__ = "desc_builder"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_id: Mapped[int | None] = mapped_column(ForeignKey("product_type.id", ondelete="CASCADE"), nullable=True)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("product_brand.id", ondelete="CASCADE"), nullable=True)
    formula_id: Mapped[int] = mapped_column(ForeignKey("formula_expression.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(nullable=False, default=0)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variables: Mapped[str] = mapped_column(Text, nullable=False)
    synonyms: Mapped[str] = mapped_column(Text, nullable=False)
    postprocess: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    type: Mapped["ProductType"] = relationship("ProductType", back_populates="desc_builders")
    brand: Mapped["ProductBrand"] = relationship("ProductBrand", back_populates="desc_builders")
    formula: Mapped["FormulaExpression"] = relationship("FormulaExpression", back_populates="desc_builders")


class DescBuilderFormulaLink(Base):
    __tablename__ = "desc_builder_formula_link"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_type_id: Mapped[int] = mapped_column(ForeignKey("formula_entity_type.id", ondelete="CASCADE"),
                                                nullable=False)
    entity_type: Mapped["FormulaEntityType"] = relationship("FormulaEntityType", back_populates="desc_builder_links")
