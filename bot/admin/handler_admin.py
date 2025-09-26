from datetime import datetime

from aiogram import Router, F
from aiogram.filters import BaseFilter, CommandStart
from aiogram.types import Message
from bot.admin.keyboards_admin import admin_basic_kb
from bot.crud_bot import show_day_sales
from config import settings
from engine import db


tg_admin_router = Router()


class AdminFilter(BaseFilter):
    is_admin: bool = True

    async def __call__(self, obj: Message):
        return (obj.from_user.id in settings.bot.telegram_admin_id) == self.is_admin


tg_admin_router.message.filter(AdminFilter())


@tg_admin_router.message(CommandStart())
async def start(m: Message):
    await m.answer('Режим админа', reply_markup=admin_basic_kb)


@tg_admin_router.message(F.text == 'Продажи сегодня')
async def show_sales(m: Message):
    async with db.tg_session() as session:
        day_sales = await show_day_sales(session=session, current_date=datetime.now().date())
    sales, returns, cardpay, amount = [], [], [], []
    for activity in day_sales:
        if not activity.return_:
            amount.append(activity.sum_)
        if activity.noncash:
            cardpay.append(activity.sum_)
        formatted_activity = [activity.time_.strftime('%H:%M'), ':-' if activity.noncash else '',
                              activity.product, f"-{activity.quantity}-", int(activity.sum_)]
        if activity.return_:
            returns.append(formatted_activity)
        else:
            sales.append(formatted_activity)
    res = '\n'.join([' '.join(map(str, line)) for line in sales])
    if returns:
        res += '\n-Возвраты:\n'
        res += '\n'.join([' '.join(map(str, line)) for line in returns])
    res += '\n'
    res += f'\nВсего {int(sum(amount))}\n\n' \
           f'Наличные {int(sum(amount) - sum(cardpay))}    '
    if sum(cardpay):
        res += f'Картой {int(sum(cardpay))}'
    await m.answer(text=res)
