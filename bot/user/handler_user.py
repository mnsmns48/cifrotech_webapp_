from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.core import user_spotted
from engine import pg_engine

tg_user_router = Router()


@tg_user_router.message(CommandStart())
async def start(m: Message) -> None:
    message_data = {'id_': m.from_user.id, 'fullname': m.from_user.full_name, 'username': m.from_user.username}
    async with pg_engine.tg_session() as session:
        await user_spotted(session=session, data=message_data)
    await m.reply('handle!! user')