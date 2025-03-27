from aiogram import Bot, Dispatcher
from aiogram.types import Update
from fastapi import APIRouter, Request

from bot.admin.handler_admin import tg_admin_router
from bot.bot_settings import bot_conf
from bot.user.handler_user import tg_user_router

bot = Bot(token=bot_conf.BOT_TOKEN.get_secret_value())
dp = Dispatcher()
dp.include_routers(tg_admin_router, tg_user_router)


async def bot_setup_webhook():
    current_webhook = await bot.get_webhook_info()
    expected_url = f"{bot_conf.WEBHOOK_URL.get_secret_value()}/webhook"
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
