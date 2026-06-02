from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column, relationship, Mapped

from models import Base

if TYPE_CHECKING:
    from models import FormulaExpression, FormulaEntityType


class DescBuilderFormulaLink(Base):
    __tablename__ = "desc_builder_formula_link"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_type_id: Mapped[int] = mapped_column(ForeignKey("formula_entity_type.id", ondelete="CASCADE"),
                                                nullable=False)
    entity_type: Mapped["FormulaEntityType"] = relationship("FormulaEntityType", back_populates="desc_builder_links")


class SpecsComposer(Base):
    __tablename__ = "specs_composer"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type_id: Mapped[int] = mapped_column(ForeignKey("product_type.id"), nullable=False)
    brand_id: Mapped[int | None] = mapped_column(ForeignKey("product_brand.id"), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    formula_id: Mapped[int] = mapped_column(ForeignKey("formula_expression.id"), nullable=False)

    formula: Mapped["FormulaExpression"] = relationship("FormulaExpression")


class SpecPath(Base):
    __tablename__ = "spec_path"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    icon: Mapped[str] = mapped_column(String(100), nullable=True)
    path: Mapped[dict] = mapped_column(JSONB, nullable=False)
    formula_id: Mapped[int] = mapped_column(ForeignKey("formula_expression.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    formula: Mapped["FormulaExpression"] = relationship(back_populates="spec_paths")

    __table_args__ = (
        UniqueConstraint("title", "formula_id", "path", name="uq_spec_path_unique"),
    )
