from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession

from core.base import Directory

from fastapi import APIRouter

router = APIRouter()


async def get_directory(session: AsyncSession):
    stmt = select(Directory).limit(1)
    result: Result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/dirs")
async def get_dirs(session):
    return await get_directory(session=session)


async def get_product(session: AsyncSession, code: int):
    return await session.get(Directory, code)


@router.get("/dirs/code")
async def get_code(session, code: int):
    return await get_product(session=session, code=code)
