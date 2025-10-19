import asyncio
import time
from typing import Dict, Callable, Any

from aiogram import BaseMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram_dialog.api.exceptions import UnknownIntent

from bot.api import get_bot_name
from config import redis_session, settings


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


class SpamMiddleware(BaseMiddleware):
    def __init__(self,
                 cooldown: int = settings.bot.spam_filter_cooldown,
                 notify_interval: int = settings.bot.spam_notify_msg):
        self.cooldown = cooldown
        self.notify_interval = notify_interval
        self.redis = redis_session()

    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Any], event: Message,
                       data: Dict[str, Any]) -> Any:
        if event.text != "/start":
            return await handler(event, data)

        user_id = event.from_user.id
        now = int(time.time())

        key_last_start = f"spam:start:{user_id}"
        key_last_notify = f"spam:notify:{user_id}"
        key_spam_message_ids = f"spam:messages:{user_id}"
        key_handled_flag = f"spam:start:handled:{user_id}"

        last_start = await self.redis.get(key_last_start)
        already_handled = await self.redis.get(key_handled_flag)

        if last_start and now - int(last_start) < self.cooldown:
            if already_handled:
                last_notify = await self.redis.get(key_last_notify)

                if not last_notify or now - int(last_notify) >= self.notify_interval:
                    msg = await event.answer(
                        "⏱ Вы уже вызывали команду /start недавно.\n"
                        "Так часто это делать не нужно — будет срабатывать спам-фильтр.\n"
                        "Вам уже доступно главное меню\nи кнопки перехода под надписью <i>Главная страница</i>",
                        parse_mode="HTML"
                    )
                    await self.redis.set(key_last_notify, now, ex=self.notify_interval)
                    await self.redis.rpush(key_spam_message_ids, msg.message_id)
                    await self.redis.expire(key_spam_message_ids, self.cooldown)

                    await asyncio.sleep(10)
                    await event.bot.delete_message(chat_id=event.chat.id, message_id=msg.message_id)

                return

        await self.redis.set(key_last_start, now, ex=self.cooldown)
        await self.redis.set(key_handled_flag, "1", ex=self.cooldown)
        return await handler(event, data)
