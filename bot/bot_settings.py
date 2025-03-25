from aiogram import Bot, Dispatcher
from pydantic.v1 import BaseSettings, SecretStr
from pydantic_settings import SettingsConfigDict

from bot.handler import aiogram_router
from cfg import BASE_DIR


class TelegramBot(BaseSettings):
    BOT_TOKEN: SecretStr
    WEBHOOK_URL: SecretStr
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")


bot_config = TelegramBot()
bot = Bot(token=bot_config.BOT_TOKEN.get_secret_value())
dp = Dispatcher()
dp.include_router(router=aiogram_router)
