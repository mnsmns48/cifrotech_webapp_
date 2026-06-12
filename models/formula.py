from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models import Base

if TYPE_CHECKING:
    from models import DescBuilderFormulaLink, SpecPath


class FormulaExpression(Base):
    __tablename__ = "formula_expression"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type_id: Mapped[int | None] = mapped_column(ForeignKey("formula_entity_type.id", ondelete="SET NULL"),
                                                       nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    entity_type: Mapped["FormulaEntityType"] = relationship(back_populates="formulas", passive_deletes=True)
    spec_paths: Mapped[list["SpecPath"]] = relationship(back_populates="formula", cascade="all, delete-orphan")


class FormulaEntityType(Base):
    __tablename__ = "formula_entity_type"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title_type: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    formulas: Mapped[list["FormulaExpression"]] = relationship(back_populates="entity_type")
    desc_builder_links: Mapped[list["DescBuilderFormulaLink"]] = relationship(back_populates="entity_type",
                                                                              cascade="all, delete-orphan")
