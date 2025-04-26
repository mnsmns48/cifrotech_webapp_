from typing import Annotated, TYPE_CHECKING

from fastapi import Depends
from fastapi_users.authentication.strategy import AccessTokenDatabase, DatabaseStrategy

from api_users.dependencies.access_token import get_access_token_db
from config import settings

if TYPE_CHECKING:
    from models import AccessToken


def get_database_strategy(access_token_db: Annotated[
    AccessTokenDatabase["AccessToken"],
    Depends(get_access_token_db)
]) -> DatabaseStrategy:
    return DatabaseStrategy(access_token_db, lifetime_seconds=settings.token.lifetime_seconds)
