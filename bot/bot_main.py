from aiogram import Bot, Dispatcher

from bot.admin.handler_admin import tg_admin_router
from bot.bot_settings import bot_config
from bot.user.handler_user import tg_user_router

bot = Bot(token=bot_config.BOT_TOKEN.get_secret_value())
dp = Dispatcher()
dp.include_routers(tg_admin_router, tg_user_router)


async def bot_set_webhook():
    current_webhook = await bot.get_webhook_info()
    expected_url = f"{bot_config.WEBHOOK_URL.get_secret_value()}/webhook"
    if current_webhook.url != expected_url:
        await bot.set_webhook(url=expected_url,
                              allowed_updates=dp.resolve_used_update_types(),
                              drop_pending_updates=True)