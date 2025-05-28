from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.requests import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api_service.schemas import RewardRangeSchema, RewardRangeLineSchema
from engine import db
from models.vendor import RewardRange, RewardRangeLine

reward_range_router = APIRouter(tags=['RewardRange-Service'])


@reward_range_router.get("/get_rewards")
async def get_reward_range(session: AsyncSession = Depends(db.scoped_session_dependency)):
    query = select(RewardRange).order_by(RewardRange.id)
    result = await session.execute(query)
    return result.scalars().all()


@reward_range_router.post("/add_reward")
async def add_reward_title(data: RewardRangeSchema, session: AsyncSession = Depends(db.scoped_session_dependency)):
    new_reward_range = RewardRange(title=data.title)
    session.add(new_reward_range)
    await session.commit()
    await session.refresh(new_reward_range)
    return new_reward_range


@reward_range_router.get("/get_reward_line/{range_id}")
async def get_reward_range(range_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    range_exists = await session.execute(select(RewardRange).filter(RewardRange.id == range_id))
    if not range_exists.scalars().first():
        raise HTTPException(status_code=404, detail="Такого профиля нет")

    query = select(RewardRangeLine).filter(RewardRangeLine.range_id == range_id).order_by(RewardRangeLine.line_from)
    result = await session.execute(query)
    return result.scalars().all()

# @reward_range_router.get("/rewards", response_model=List[RewardRangeSchema])
# async def get_rewards(session: AsyncSession = Depends(db.scoped_session_dependency)):
#     query = select(RewardRange).options(selectinload(RewardRange.lines))
#     result = await session.execute(query)
#     reward_ranges = result.scalars().all()
#
#     return [
#         RewardRangeSchema(
#             id=reward.id,
#             title=reward.title,
#             lines=[RewardRangeLineSchema.model_validate(line) for line in reward.lines]
#         ) for reward in reward_ranges
#     ]


# @reward_range_router.post("/add_reward_line", response_model=RewardRangeLineSchema)
# async def add_range_reward_line(data: RewardRangeLineSchema,
#                                 session: AsyncSession = Depends(db.scoped_session_dependency)):
#     query = await session.execute(select(RewardRange).where(RewardRange.id == data.range_id))
#     reward_range = query.scalar_one_or_none()
#
#     if not reward_range:
#         raise HTTPException(status_code=404, detail="RewardRange не найден")
#
#     validated_data = RewardRangeLineSchema.cls_validate(data, exclude_id=True)
#     new_reward_line = RewardRangeLine(**validated_data)
#     session.add(new_reward_line)
#     await session.commit()
#     await session.refresh(new_reward_line)
#     return {'result': f"✅ Создана новая строка"}


# @reward_range_router.put("/reward_line/{line_id}")
# async def update_range_reward_line(data: RewardRangeLineSchema)


# @reward_range_router.delete("/delete_reward_line/{line_id}")
# async def update_range_reward_line(line_id: int,
#                                    session: AsyncSession = Depends(db.scoped_session_dependency)):
#     query = await session.get(RewardRangeLine, line_id)
#     if not query:
#         return {"error": f"Строка {line_id} не найдена"}
#     await session.delete(query)
#     await session.commit()
#     return {"result": f"Строка {line_id} удалена"}
