from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    code: Mapped[int] = mapped_column(primary_key=True)


class Avail(Base):
    __tablename__ = "avail"
    type_: Mapped[str]
    brand: Mapped[str]
    code: Mapped[int]
    product: Mapped[str]
    quantity: Mapped[int]
    price: Mapped[int]


class s_main(Base):
    __tablename__ = "main"
    title: Mapped[str] = mapped_column(primary_key=True)
    brand: Mapped[str]
    # category: Mapped[]
    # advantage: Mapped[]
    # disadvantage: Mapped[]
    # total_score: Mapped[]
    # announced: Mapped[]
    # release_date: Mapped[]
