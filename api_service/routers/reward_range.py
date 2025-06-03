from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from api_service.schemas import RewardRangeSchema, RewardRangeLineSchema
from api_service.utils import update_instance_fields
from engine import db
from models.vendor import RewardRange, RewardRangeLine

reward_range_router = APIRouter(tags=['RewardRange-Service'])


###################### reward_ranges ##############################


async def check_profile_exists(range_id: int, session: AsyncSession, negative_result: str):
    result = await session.execute(select(RewardRange).filter(RewardRange.id == range_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail=negative_result)


@reward_range_router.get("/get_rewards")
async def get_reward_range(session: AsyncSession = Depends(db.scoped_session_dependency)):
    query = select(RewardRange).order_by(RewardRange.id)
    result = await session.execute(query)
    return result.scalars().all()


@reward_range_router.post("/add_reward")
async def add_reward_title(data: RewardRangeSchema, session: AsyncSession = Depends(db.scoped_session_dependency)):
    existing_profiles = await session.execute(select(RewardRange))
    profiles = existing_profiles.scalars().all()
    is_default_value = len(profiles) == 0
    new_reward_range = RewardRange(title=data.title, is_default=is_default_value)
    session.add(new_reward_range)
    await session.commit()
    await session.refresh(new_reward_range)
    return new_reward_range


@reward_range_router.delete("/delete_range_profile/{range_id}")
async def delete_reward_range_profile(range_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    await check_profile_exists(range_id, session, "Такого профиля нет")
    await session.execute(delete(RewardRange).filter(RewardRange.id == range_id))
    await session.commit()
    return 'Профиль удален'


@reward_range_router.put("/update_range_profile/{range_id}")
async def update_reward_range(range_id: int, update_data: RewardRangeSchema,
                              session: AsyncSession = Depends(db.scoped_session_dependency)):
    profile = await session.get(RewardRange, range_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Нельзя изменить несуществующий профиль")
    await update_instance_fields(profile, update_data.model_dump(), session)
    return "Профиль успешно обновлен"


###################### reward_range_lines ##############################

@reward_range_router.get("/get_reward_lines/{range_id}")
async def get_reward_range(range_id: int, session: AsyncSession = Depends(db.scoped_session_dependency)):
    await check_profile_exists(range_id, session, "Такого профиля нет")
    query = select(RewardRangeLine).filter(RewardRangeLine.range_id == range_id).order_by(RewardRangeLine.line_from)
    result = await session.execute(query)
    return result.scalars().all()


@reward_range_router.post("/add_reward_range_line")
async def add_reward_title(data: RewardRangeLineSchema, session: AsyncSession = Depends(db.scoped_session_dependency)):
    await check_profile_exists(data.range_id, session, "Нельзя создать строку для несуществующего профиля")
    new_reward_line = RewardRangeLine(**data.model_dump())
    session.add(new_reward_line)
    await session.commit()
    await session.refresh(new_reward_line)
    return "Новая строка создана"


@reward_range_router.delete("/delete_reward_line/{line_id}")
async def delete_range_reward_line(line_id: int,
                                   session: AsyncSession = Depends(db.scoped_session_dependency)):
    query = await session.get(RewardRangeLine, line_id)
    print(query)
    if not query:
        raise HTTPException(status_code=404, detail="Нельзя удалить то, чего нет")
    await session.delete(query)
    await session.commit()
    return "Строка удалена"


@reward_range_router.put("/update_reward_line/{line_id}")
async def add_reward_title(line_id: int, data: RewardRangeLineSchema,
                           session: AsyncSession = Depends(db.scoped_session_dependency)):
    query = await session.get(RewardRangeLine, line_id)
    if not query:
        raise HTTPException(status_code=404, detail="Нельзя обновить то чего не существует")

    await update_instance_fields(query, data.model_dump(), session)
    return "Строка обновлена"
