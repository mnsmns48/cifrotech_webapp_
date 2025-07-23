from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class HUbMenuLevel(Base):
    __tablename__ = "hub_menu_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    sort_order: Mapped[int] = mapped_column(default=0, index=True)
    label: Mapped[str]
    icon: Mapped[Optional[str]] = mapped_column(nullable=True)
    parent_id: Mapped[int] = mapped_column(nullable=False, index=True)
