from pathlib import Path
from typing import List, Union
import redis.asyncio as redis

from pydantic import PostgresDsn, field_validator, Field

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent


class CustomConfigSettings(BaseSettings):
    class Config:
        env_file = BASE_DIR / ".env"
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
    photo_path_order: str
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


class Settings(CustomConfigSettings):
    db: DBSettings = DBSettings()
    api: APISettings = APISettings()
    token: Token = Token()
    redis: RedisSettings = RedisSettings()
    parsing: ParsingSettings = ParsingSettings()


settings = Settings()


def redis_session():
    return redis.from_url(settings.redis.redis_url, decode_responses=True)
