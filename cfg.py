from dataclasses import dataclass
from pathlib import Path

from environs import Env
from pydantic.v1 import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
PHOTO_DIR = str()


def transfer(s: str) -> tuple:
    _list = list()
    _list.append(s.split(",")[0])
    _list.append(int(s.split(",")[1]))
    return tuple(_list)


@dataclass()
class Remote_PG_DB:
    remote_db_user: str
    remote_db_password: str
    remote_db_host: str
    remote_db_port: int
    remote_db_name: str
    ssh_address_and_host: tuple
    ssh_username: str
    ssh_password: str
    ssh_bind_address: tuple


@dataclass
class Settings:
    remote_pg_db: Remote_PG_DB


def load_config(path: str = None):
    env = Env()
    env.read_env()

    return Settings(
        remote_pg_db=Remote_PG_DB(
            remote_db_user=env.str("REMOTE_DB_USER"),
            remote_db_password=env.str("REMOTE_DB_PASSWORD"),
            remote_db_host=env.str("REMOTE_DB_HOST"),
            remote_db_port=env.int("REMOTE_DB_PORT"),
            remote_db_name=env.str("REMOTE_DB_NAME"),
            ssh_address_and_host=transfer(env.str("SSH_ADDRESS_AND_HOST")),
            ssh_username=env.str("SSH_USERNAME"),
            ssh_password=env.str("SSH_PASSWORD"),
            ssh_bind_address=transfer(env.str("SSH_BIND_ADDRESS")),
        ),
    )


settings = load_config("..env")


class CoreConfig(BaseSettings):
    db_url: str = (
        "postgresql+asyncpg://postgres:534534@localhost:5433/activity_server"
    )
    db_echo: bool = False


core_config = CoreConfig()
