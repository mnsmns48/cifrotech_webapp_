from pathlib import Path
from typing import List, Union

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
    bearer_token_url: str = '/auth/login'


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


class Settings(CustomConfigSettings):
    db: DBSettings = DBSettings()
    api: APISettings = APISettings()
    token: Token = Token()


settings = Settings()
