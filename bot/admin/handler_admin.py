from aiogram import Router
from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.bot_settings import bot_conf

tg_admin_router = Router()


class AdminFilter(BaseFilter):
    is_admin: bool = True

    async def __call__(self, obj: Message):
        return (obj.from_user.id in bot_conf.TELEGRAM_ADMIN_ID) == self.is_admin


tg_admin_router.message.filter(AdminFilter())


@tg_admin_router.message()
async def start(m: Message) -> None:
    await m.reply('handle!! admin')
