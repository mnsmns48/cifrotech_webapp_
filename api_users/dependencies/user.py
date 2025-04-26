from typing import Annotated, TYPE_CHECKING

from fastapi import Depends

from engine import db
from models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_db(session: Annotated["AsyncSession", Depends(db.session_getter)]):
    yield User.get_db(session=session)
