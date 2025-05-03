from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class TgBotOptions(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    username: Mapped[str] = mapped_column(primary_key=True)
    main_pic: Mapped[str] = mapped_column(nullable=True)
