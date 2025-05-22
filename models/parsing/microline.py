from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class Microline(Base):
    code: Mapped[int] = mapped_column(primary_key=True, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(nullable=False)
    shipment: Mapped[str] = mapped_column(nullable=True)
    warranty: Mapped[str] = mapped_column(nullable=True)
    input_price: Mapped[float] = mapped_column(nullable=True)
    pic: Mapped[str] = mapped_column(nullable=True)
    optional: Mapped[str] = mapped_column(nullable=True)