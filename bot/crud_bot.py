from datetime import datetime, date

import sqlalchemy
from sqlalchemy import select, Result, update, func, cast, Date, Text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import Guests, TgBotOptions, Activity


async def user_spotted(session: AsyncSession, data: dict) -> None:
    await session.execute(insert(Guests), data)
    await session.commit()


async def get_option_value(session: AsyncSession, username, field):
    stmt = select(TgBotOptions).filter(TgBotOptions.username == username)
    result: Result = await session.execute(stmt)
    option_obj = result.scalars().first()
    return getattr(option_obj, field) if option_obj else None


async def add_bot_options(session: AsyncSession, **kwargs):
    if kwargs:
        await session.execute(insert(TgBotOptions).values(kwargs))
        await session.commit()


async def update_bot(session: AsyncSession, **kwargs):
    if kwargs:
        await session.execute(update(TgBotOptions).filter(TgBotOptions.username == kwargs.get('username'))
                              .values(main_pic=kwargs.get('main_pic')))
        await session.commit()


async def show_day_sales(session: AsyncSession, current_date: date):
    stmt = sqlalchemy.text(f"""SELECT * from activity
        where CAST(activity.time_ AS DATE) = '{current_date}'
        ORDER BY activity.time_ """)
    response: Result = await session.execute(stmt)
    return response.fetchall()
