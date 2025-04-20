from dataclasses import dataclass
from pathlib import Path
from environs import Env
from pydantic.v1 import BaseSettings

BASE_DIR = Path(__file__).resolve().parent

disabled_buttons = ['Смартфоны', 'Планшеты', 'Кнопочные телефоны', 'Смарт часы и фитнес трекеры']
dir_with_desc = [12, 80, 81, 82, 83, 84, 87, 101]


@dataclass
class Settings:
    local_db_username: str
    local_db_password: str
    db_server: str
    local_db_port: str
    local_db_name: str
    photo_path: str
    docs_url: str
    description_db_name: str
    backend_url: str
    digitaltube: str
    cors: list


def load_config(path: str = None):
    env = Env()
    env.read_env()

    return Settings(
        local_db_username=env.str("LOCAL_DB_USERNAME"),
        local_db_password=env.str("LOCAL_DB_PASSWORD"),
        db_server=env.str("DB_SERVER"),
        local_db_port=env.str("LOCAL_DB_PORT"),
        local_db_name=env.str("LOCAL_DB_NAME"),
        photo_path=env.str("PHOTO_PATH"),
        docs_url=env.str("DOCS_URL"),
        description_db_name=env.str("DESCRIPTION_DB_NAME"),
        backend_url=env.str("BACKEND_URL"),
        digitaltube=env.str("DIGITALTUBE_URL"),
        cors=env.list("CORS")
    )


settings = load_config("..env")


class CoreConfig(BaseSettings):
    as_stocktable: str = (
        f"postgresql+asyncpg://{settings.local_db_username}:{settings.local_db_password}"
        f"@{settings.db_server}:{settings.local_db_port}/{settings.local_db_name}"
    )
    phones_desc_db: str = (
        f"postgresql+asyncpg://{settings.local_db_username}:{settings.local_db_password}"
        f"@localhost:{settings.local_db_port}/{settings.description_db_name}"
    )
    db_echo: bool = False


core_config = CoreConfig()