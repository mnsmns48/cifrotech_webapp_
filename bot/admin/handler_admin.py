import html
from datetime import datetime
from html import escape
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
    def format_lines(lines):
        return '\n'.join([' '.join(line) for line in lines])

    async with db.tg_session() as session:
        day_sales = await show_day_sales(session=session, current_date=datetime.now().date())

    sales, returns, cardpay, amount = [], [], [], []

    for activity in day_sales:
        if not activity.return_:
            amount.append(activity.sum_)
        if activity.noncash:
            cardpay.append(activity.sum_)

        formatted_activity = [activity.time_.strftime('%H:%M'), '➚' if activity.noncash else '',
                              escape(activity.product), f"<i>-{activity.quantity}-</i>", f"<b>{int(activity.sum_)}</b>"]

        if activity.return_:
            returns.append(formatted_activity)
        else:
            sales.append(formatted_activity)

    res = format_lines(sales)

    if returns:
        res += '\n\n<b>Возвраты:</b>\n'
        res += format_lines(returns)

    cash_total = int(sum(amount) - sum(cardpay))
    card_total = int(sum(cardpay))
    total = int(sum(amount))

    res += f'\n\nНаличные: <b>{cash_total}</b>'
    if card_total:
        res += f'    Картой: <b>{card_total}</b>'

    res += f'\n\n<b>Всего: {total}</b>'

    await m.answer(text=res, parse_mode="HTML")
