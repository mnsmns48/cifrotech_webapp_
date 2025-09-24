from collections import Counter
from datetime import date
from typing import List

import sqlalchemy
from sqlalchemy import select, Result, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app_utils import format_datetime_ru
from bot.user.schemas import HubMenuLevel, HubStockResponse, HubStockItem
from models import Guests, TgBotOptions, HUbMenuLevel, HUbStock, ProductOrigin


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
    stmt = sqlalchemy.text(
        f"""
        SELECT * from activity
        where CAST(activity.time_ AS DATE) = '{current_date}'
        ORDER BY activity.time_
""")
    response: Result = await session.execute(stmt)
    return response.fetchall()


async def get_menu_levels(session: AsyncSession, parent_id: int = 1) -> List[HubMenuLevel]:
    query = select(HUbMenuLevel).where(HUbMenuLevel.parent_id == parent_id).order_by(HUbMenuLevel.sort_order)
    execute = await session.execute(query)
    levels = execute.scalars().all()
    result: List[HubMenuLevel] = list()
    for level in levels:
        result.append(HubMenuLevel.model_validate(level))
    return result


async def get_labels_by_ids(session: AsyncSession, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    query = select(HUbMenuLevel).where(HUbMenuLevel.id.in_(ids))
    execute = await session.execute(query)
    levels = execute.scalars().all()
    return {level.id: level.label for level in levels}


async def get_hubstock_items(session: AsyncSession, path_id: int) -> HubStockResponse:
    stmt = (
        select(
            HUbStock.output_price,
            HUbStock.updated_at,
            HUbStock.origin,
            ProductOrigin.title
        )
        .join(ProductOrigin, ProductOrigin.origin == HUbStock.origin)
        .where(HUbStock.path_id == path_id)
    )

    result = await session.execute(stmt)
    rows = result.all()

    items = [
        HubStockItem(title=row.title, price=row.output_price, origin=row.origin)
        for row in rows if row.output_price is not None
    ]

    updated_dates = [row.updated_at for row in rows]
    most_common_updated_at = None
    if updated_dates:
        most_common_updated_at = Counter(updated_dates).most_common(1)[0][0]

    formatted_date = format_datetime_ru(most_common_updated_at) if most_common_updated_at else None

    return HubStockResponse(items=items, most_common_updated_at=formatted_date)
