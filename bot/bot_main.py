import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramRetryAfter
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import Update
from fastapi import APIRouter, Request

from bot.admin.handler_admin import tg_admin_router
from bot.middleware import DBSessionMiddleware, UnknownIntentMiddleware
from bot.user.handler_user import tg_user_router
from config import settings, redis_session
from engine import db

storage = RedisStorage(redis_session(),
                       key_builder=DefaultKeyBuilder(prefix="Hub_user_bot", with_destiny=True),
                       state_ttl=settings.bot.ttl_redis_key,
                       data_ttl=settings.bot.ttl_redis_key)
bot = Bot(token=settings.bot.bot_token.get_secret_value())
dp = Dispatcher(storage=storage)
dp.message.middleware(DBSessionMiddleware(db.session_factory))
dp.callback_query.middleware(DBSessionMiddleware(db.session_factory))
dp.update.middleware(UnknownIntentMiddleware())
dp.include_routers(tg_admin_router, tg_user_router)


async def bot_setup_webhook():
    expected_url = f"{settings.bot.webhook_url.get_secret_value()}/webhook"
    current_webhook = await bot.get_webhook_info()

    if current_webhook.url != expected_url:
        try:
            await bot.delete_webhook(drop_pending_updates=True, request_timeout=5)
            await asyncio.sleep(3)
            await bot.set_webhook(url=expected_url,
                                  allowed_updates=dp.resolve_used_update_types(),
                                  drop_pending_updates=True)
        except TelegramRetryAfter as e:
            logging.warning(f"Flood control: retry after {e.retry_after} seconds")
            await asyncio.sleep(e.retry_after)

    bot_obj = await bot.me()
    return bot_obj.username


bot_fastapi_router = APIRouter()


@bot_fastapi_router.post("/webhook")
async def webhook(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
