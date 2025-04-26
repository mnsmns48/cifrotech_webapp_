from aiogram import Router, F
from aiogram.filters import BaseFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiohttp import ClientSession
from bot.admin.keyboards_admin import admin_basic_choice_kb, admin_basic_kb
from bot.bot_settings import bot_conf
# from bot.core import parse_product_message, working_under_product_list
from bot.crud_bot import show_day_sales
from bot.utils import filter_keys
from engine import db
from utils import sanitize_emoji

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
    async with db.tg_session() as session:
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


# @tg_admin_router.callback_query(F.data == 'process_vendor_message')
# async def callback_process_vendor_message(c: CallbackQuery, state: FSMContext):
#     await c.answer('ok')
#     context = await state.get_data()
#     msg = context.get('msg')
#     string_data_key = 'caption' if 'caption' in msg else 'text' if 'text' in msg else None
#     parsed_data_list: list[dict] = parse_product_message(text=sanitize_emoji(msg.get(string_data_key)))
#     async with pg_engine.tg_session() as tg_session, ClientSession() as cl_session:
#         await working_under_product_list(pg_session=tg_session, cl_session=cl_session, products=parsed_data_list)



@tg_admin_router.message()
async def get_forwarding_message(m: Message, state: FSMContext):
    await state.update_data(msg=filter_keys(m.model_dump()))
    await m.answer(text='?', reply_markup=admin_basic_choice_kb.as_markup())
