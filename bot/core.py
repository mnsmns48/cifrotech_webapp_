from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Guests


async def user_spotted(session: AsyncSession, data: dict) -> None:
    await session.execute(insert(Guests), data)
    await session.commit()
