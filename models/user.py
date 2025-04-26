from datetime import datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from types import var_types


class IdIntPkMixin:
    id: Mapped[int] = mapped_column(primary_key=True)


class AdditionalUserFields:
    phone_number: Mapped[int]
    vk_id: Mapped[int] = mapped_column(nullable=True)
    full_name: Mapped[str] = mapped_column(nullable=True)
    birthday: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=True)
    address: Mapped[int] = mapped_column(nullable=True)


class User(Base,
           IdIntPkMixin,
           SQLAlchemyBaseUserTable[var_types.UserIdType],
           AdditionalUserFields):
    __tablename__ = 'users'
