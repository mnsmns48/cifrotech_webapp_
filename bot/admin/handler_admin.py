import html
from collections import defaultdict
from datetime import datetime
from html import escape
from typing import Dict, List

from aiogram import Router, F
from aiogram.filters import BaseFilter, CommandStart
from aiogram.types import Message

from api_service.schemas.api_v1_schemas import SaleItemScheme
from bot.admin.keyboards_admin import admin_basic_kb
from bot.crud_bot import show_day_sales, get_last_guests
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
    def format_grouped(group: dict[str, list[str]]) -> str:
        blocks: list[str] = list()
        for time, lines in group.items():
            time_header = f"<pre>{time}  </pre>"
            joined_lines = '\n'.join(lines)
            block = f"{time_header}\n{joined_lines}"
            blocks.append(block)
        return '\n\n'.join(blocks)

    async with db.tg_session() as session:
        day_sales: List[SaleItemScheme] = await show_day_sales(session=session, current_date=datetime.now().date())

    grouped_regular: dict[str, list[str]] = defaultdict(list)
    grouped_returns: dict[str, list[str]] = defaultdict(list)
    cash_total, card_total = 0.0, 0.0

    for sale in day_sales:
        time_key = sale.time_.strftime('%H:%M')
        line = list()
        if sale.noncash:
            line.append('➚')
        line.append(sale.product)
        line.append(f"-<i>{sale.quantity}</i>-")

        if sale.return_:
            line.append(f"<code>-{sale.sum_:.0f}</code>")
        else:
            line.append(f"<code>{sale.sum_:.0f}</code>")

        line.append(f" :{sale.remain}" if sale.remain is not None else "")
        formatted = ' '.join(line)

        if sale.return_:
            grouped_returns[time_key].append(formatted)
            if sale.noncash:
                card_total -= sale.sum_
            else:
                cash_total -= sale.sum_
        else:
            grouped_regular[time_key].append(formatted)
            if sale.noncash:
                card_total += sale.sum_
            else:
                cash_total += sale.sum_

    body = format_grouped(grouped_regular)
    if grouped_returns:
        body += '\n\n<b>Возвраты:</b>\n' + format_grouped(grouped_returns)

    summary = (f"\n\nНаличные: {cash_total:.0f}    "
               f"Картой: {card_total:.0f}\n"
               f"Всего: <b>{cash_total + card_total:.0f}</b>")

    await m.answer(text=body + summary, parse_mode="HTML")


@tg_admin_router.message(F.text == 'Последние гости')
async def show_sales(m: Message):
    async with db.tg_session() as pg_session:
        guests = await get_last_guests(session=pg_session)

    if not guests:
        await m.answer("Нет гостей")
        return

    text = ["<b>Последние гости:</b>\n"]

    for g in guests:
        fullname = g["fullname"] or ""
        username = f"@{g['username']}" if g["username"] else ""

        text.append(f"<b>{g['date']}</b> {fullname} {username}")

    await m.answer("\n".join(text), parse_mode="HTML")
