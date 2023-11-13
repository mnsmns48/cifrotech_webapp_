from dataclasses import dataclass
from pathlib import Path

from environs import Env
from pydantic.v1 import BaseSettings




@dataclass
class Settings:
    local_db_username: str
    local_db_password: str
    local_db_port: str
    local_db_name: str
    photo_path: str
    description_db_name: str


def load_config(path: str = None):
    env = Env()
    env.read_env()

    return Settings(
        local_db_username=env.str("LOCAL_DB_USERNAME"),
        local_db_password=env.str("LOCAL_DB_PASSWORD"),
        local_db_port=env.str("LOCAL_DB_PORT"),
        local_db_name=env.str("LOCAL_DB_NAME"),
        photo_path=env.str("PHOTO_PATH"),
        description_db_name=env.str("DESCRIPTION_DB_NAME")
    )


settings = load_config("..env")
BASE_DIR = Path(__file__).resolve().parent


class CoreConfig(BaseSettings):
    as_stocktable: str = (
        f"postgresql+asyncpg://{settings.local_db_username}:{settings.local_db_password}"
        f"@localhost:{settings.local_db_port}/{settings.local_db_name}"
    )
    phones_desc_db: str = (
        f"postgresql+asyncpg://{settings.local_db_username}:{settings.local_db_password}"
        f"@localhost:{settings.local_db_port}/{settings.description_db_name}"
    )
    db_echo: bool = False


core_config = CoreConfig()
