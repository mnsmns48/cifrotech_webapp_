from datetime import datetime
from typing import TYPE_CHECKING

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable, SQLAlchemyUserDatabase
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from var_types import var_types

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AdditionalUserFields:
    vk_id: Mapped[int] = mapped_column(nullable=True)
    full_name: Mapped[str] = mapped_column(nullable=True)
    birthday: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=True)
    address: Mapped[int] = mapped_column(nullable=True)


class User(Base,
           SQLAlchemyBaseUserTable[var_types.UserIdType],
           AdditionalUserFields):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[int] = mapped_column(index=True, unique=True)

    @classmethod
    def get_db(cls, session: "AsyncSession"):
        return SQLAlchemyUserDatabase(session, cls)
