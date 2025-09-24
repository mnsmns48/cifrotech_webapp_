import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import APIRouter, Request

from bot.admin.handler_admin import tg_admin_router
from bot.middleware import DBSessionMiddleware
from bot.user.handler_user import tg_user_router
from config import settings
from engine import db

storage = MemoryStorage()
bot = Bot(token=settings.bot.bot_token.get_secret_value())
dp = Dispatcher()
dp.message.middleware(DBSessionMiddleware(db.session_factory))
dp.callback_query.middleware(DBSessionMiddleware(db.session_factory))
dp.include_routers(tg_admin_router, tg_user_router)


async def bot_setup_webhook():
    await bot.delete_webhook(drop_pending_updates=True, request_timeout=5)
    await asyncio.sleep(3)
    current_webhook = await bot.get_webhook_info()
    expected_url = f"{settings.bot.webhook_url.get_secret_value()}/webhook"
    if current_webhook.url != expected_url:
        await bot.set_webhook(url=expected_url,
                              allowed_updates=dp.resolve_used_update_types(),
                              drop_pending_updates=True)
    bot_obj = await bot.me()
    return bot_obj.username


bot_fastapi_router = APIRouter()


@bot_fastapi_router.post("/webhook")
async def webhook(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
