from sqlalchemy.orm import DeclarativeBase, declared_attr, Mapped, mapped_column


class Base(DeclarativeBase):
    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class ProgressUUID(Base):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, unique=True)
    progress: Mapped[str] = mapped_column(unique=True, nullable=False)