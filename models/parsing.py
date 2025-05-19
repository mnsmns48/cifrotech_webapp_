from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class ParsingLog(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    log_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    request_id: Mapped[str] = mapped_column(unique=True, nullable=False)
    user: Mapped[str] = mapped_column(unique=True, nullable=False)
    vendor_name: Mapped[str] = mapped_column(unique=True, nullable=False)
    parsing_title: Mapped[str] = mapped_column(unique=True, nullable=False)
    parsing_url: Mapped[str] = mapped_column(unique=True, nullable=False)
    result: Mapped[bool] = mapped_column(nullable=True)
