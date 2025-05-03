from typing import Annotated, TYPE_CHECKING

from fastapi import Depends

from api_users.dependencies.user import get_user_db
from api_users.user_manager import UserManager

if TYPE_CHECKING:
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase


async def get_user_manager(users_db: Annotated["SQLAlchemyUserDatabase", Depends(get_user_db)]):
    yield UserManager(users_db)


