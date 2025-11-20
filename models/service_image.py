from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class ServiceImage(Base):
    __tablename__ = "service_image"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    var: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]
