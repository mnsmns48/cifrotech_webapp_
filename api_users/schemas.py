from fastapi_users import schemas
from datetime import datetime
from typing import Optional
from var_types import var_types


class UserBaseScheme:
    vk_id: Optional[int] = None
    full_name: Optional[str] = None
    birthday: Optional[datetime] = None
    address: Optional[int] = None


class UserRead(UserBaseScheme, schemas.BaseUser[var_types.UserIdType]):
    phone_number: Optional[int] = None


class UserCreate(UserBaseScheme, schemas.BaseUserCreate):
    phone_number: int


class UserUpdate(UserBaseScheme, schemas.BaseUserUpdate):
    phone_number: Optional[int] = None
