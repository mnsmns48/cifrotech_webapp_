from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Vendor, ParsingLog


async def get_parsing_request(pg_session: AsyncSession, request: str, limit: int = 1) -> bool | None:
    query = select(ParsingLog).filter(ParsingLog.request == request).limit(limit)
    result = await pg_session.execute(query)
