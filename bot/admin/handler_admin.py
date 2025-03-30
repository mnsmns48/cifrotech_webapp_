import json

from aiogram import Router, F
from aiogram.filters import BaseFilter, CommandStart
from aiogram.types import Message

from bot.admin.keyboards_admin import admin_basic_kb
from bot.bot_settings import bot_conf
from bot.core import show_day_sales
from engine import pg_engine

tg_admin_router = Router()


class AdminFilter(BaseFilter):
    is_admin: bool = True

    async def __call__(self, obj: Message):
        return (obj.from_user.id in bot_conf.TELEGRAM_ADMIN_ID) == self.is_admin


tg_admin_router.message.filter(AdminFilter())


@tg_admin_router.message(CommandStart())
async def start(m: Message):
    await m.answer('Режим админа', reply_markup=admin_basic_kb)


@tg_admin_router.message(F.text == 'Продажи сегодня')
async def show_sales(m: Message):
    async with pg_engine.tg_session() as session:
        day_sales = await show_day_sales(session=session)
    sales, returns, cardpay, amount = [], [], [], []
    for activity in day_sales:
        if not activity.return_:
            amount.append(activity.sum_)
        if activity.noncash:
            cardpay.append(activity.sum_)
        formatted_activity = [activity.time_.strftime('%H:%M'),
                              activity.product,
                              int(activity.quantity) if activity.quantity % 1 == 0 else activity.quantity,
                              int(activity.sum_) if activity.sum_ % 1 == 0 else activity.sum_,
                              '-card' if activity.noncash else '']
        if activity.return_:
            returns.append(formatted_activity)
        else:
            sales.append(formatted_activity)
    res = '\n'.join([' '.join(map(str, line)) for line in sales])
    if returns:
        res += '\n-Возвраты:\n'
        res += '\n'.join([' '.join(map(str, line)) for line in returns])
    res += '\n'
    res += f'\nВсего {int(sum(amount))}\n' \
           f'Наличные {int(sum(amount) - sum(cardpay))}    '
    if sum(cardpay):
        res += f'Картой {int(sum(cardpay))}'
    await m.answer(text=res)


def remove_null_values(data):
    if isinstance(data, dict):
        return {key: remove_null_values(value) for key, value in data.items() if value is not None}
    elif isinstance(data, list):
        return [remove_null_values(item) for item in data if item is not None]
    else:
        return data


@tg_admin_router.message()
async def get_forwarding_message(m: Message):
    await m.answer(text='ok')
    message_dict = m.model_dump()
    filtered_dict = remove_null_values(message_dict)
    message_json = json.dumps(filtered_dict, indent=4, ensure_ascii=False)

    print(message_json)
