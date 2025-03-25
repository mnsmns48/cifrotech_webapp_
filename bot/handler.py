from aiogram import Router
from aiogram.types import Message

aiogram_router = Router()


@aiogram_router.message()
async def start(m: Message) -> None:
    await m.reply('handle!!')
