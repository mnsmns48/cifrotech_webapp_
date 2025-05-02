from datetime import datetime

from bot.crud_bot import show_day_sales
from engine import db


async def callable_func():
    current_date = datetime.fromisocalendar(year=2025, week=16, day=3).date()
    async with db.tg_session() as session:
        await show_day_sales(session=session, current_date=current_date)
