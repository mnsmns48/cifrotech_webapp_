from typing import List

from fastapi import APIRouter, Depends
from fastapi.requests import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import RewardRangeSchema
from engine import db
from models.vendor import RewardRange

reward_range_router = APIRouter(tags=['RewardRange-Service'])


@reward_range_router.get("/rewards", response_model=List[RewardRangeSchema])
async def get_rewards(request: Request, session: AsyncSession = Depends(db.scoped_session_dependency)):
    query = select(RewardRange).options(selectinload(RewardRange.lines))
    result = await session.execute(query)
    reward_ranges = result.scalars().all()

    return [RewardRangeSchema.from_orm(reward) for reward in reward_ranges]

