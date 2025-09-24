import logging

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_dialog.api.exceptions import UnknownIntent

from bot.api import get_bot_name


class DBSessionMiddleware(BaseMiddleware):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def __call__(self, handler, event, data):
        async with self.session_factory() as session:
            data["session"] = session
            return await handler(event, data)


class UnknownIntentMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except UnknownIntent as e:
            bot = data.get("bot")
            user = data.get("event_from_user")
            if not bot or not user:
                return None
            bot_name = await get_bot_name()
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🔄 Старт",
                        url=f"https://t.me/{bot_name}?start=start"
                    )]
                ]
            )
            if bot_name:
                await bot.send_message(
                    chat_id=user.id,
                    text="Пожалуйста, начните заново:",
                    reply_markup=keyboard
                )
            return None
