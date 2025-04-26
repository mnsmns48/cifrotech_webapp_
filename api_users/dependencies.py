from typing import Annotated, TYPE_CHECKING

from fastapi import Depends
from fastapi_users.authentication.strategy import AccessTokenDatabase, DatabaseStrategy

from api_users.backend import UserManager
from config import settings
from engine import db
from models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
    from models import AccessToken


async def get_access_token_db(session: Annotated["AsyncSession", Depends(db.session_getter)]):
    yield AccessToken.get_db(session=session)


async def get_user_db(session: Annotated["AsyncSession", Depends(db.session_getter)]):
    yield User.get_db(session=session)


async def get_user_manager(users_db: Annotated["SQLAlchemyUserDatabase", Depends(get_user_db)]):
    yield UserManager(users_db)


def get_database_strategy(access_token_db: Annotated[
    AccessTokenDatabase["AccessToken"],
    Depends(get_access_token_db)
]) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=settings.token.lifetime_seconds)
