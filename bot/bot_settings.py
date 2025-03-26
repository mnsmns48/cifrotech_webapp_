from typing import List

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict, BaseSettings
from cfg import BASE_DIR


class TelegramBot(BaseSettings):
    BOT_TOKEN: SecretStr
    WEBHOOK_URL: SecretStr
    TELEGRAM_ADMIN_ID: List[int]
    model_config = SettingsConfigDict(env_file=BASE_DIR / "bot/bot.env", env_file_encoding="utf-8")


bot_config = TelegramBot()
