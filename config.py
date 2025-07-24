import os
from pathlib import Path
from typing import List, Union
import redis.asyncio as redis
from dotenv import load_dotenv

from pydantic import PostgresDsn, field_validator, Field, SecretStr

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent

BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                                 "Chrome/100.0.4896.75 Safari/537.36",
                   "Accept-Language": "en-US,en;q=0.9",
                   "Referer": "https://google.com"}

load_dotenv(dotenv_path=BASE_DIR / ".env")
secret_env_path = os.getenv("SP")
if secret_env_path:
    load_dotenv(dotenv_path=secret_env_path)
else:
    raise RuntimeError("Не указана переменная SP с путём до файла .env с ключами")


class CustomConfigSettings(BaseSettings):
    class Config:
        env_file = secret_env_path
        case_sensitive = False
        extra = "allow"


class DBSettings(CustomConfigSettings):
    url: PostgresDsn


class Token(CustomConfigSettings):
    reset_password_token_secret: str
    verification_token_secret: str
    lifetime_seconds: int
    bearer_token_url: str = '/login'


class APISettings(CustomConfigSettings):
    photo_path: str
    backend_url: str
    digitaltube_url: str
    docs_url: str
    cors: Union[str, List[str]] = Field(...)

    @field_validator("cors", mode="before")
    def parse_cors_line(cls, value: str) -> list[str] | str:
        if isinstance(value, str):
            return value.split(",")
        return value


class RedisSettings(CustomConfigSettings):
    redis_url: str


class ParsingSettings(CustomConfigSettings):
    browser_headless: bool


class BotSettings(CustomConfigSettings):
    bot_token: SecretStr
    telegram_admin_id: List[int]
    webhook_url: SecretStr


class S3Settings(CustomConfigSettings):
    s3_url: str
    bucket_name: str
    s3_access_key: str
    s3_secret_access_key: str
    region: str
    s3_hub_prefix: str

class Settings(CustomConfigSettings):
    db: DBSettings = DBSettings()
    api: APISettings = APISettings()
    token: Token = Token()
    redis: RedisSettings = RedisSettings()
    parsing: ParsingSettings = ParsingSettings()
    bot: BotSettings = BotSettings()
    s3: S3Settings = S3Settings()


settings = Settings()


def redis_session():
    return redis.from_url(settings.redis.redis_url, decode_responses=True)
