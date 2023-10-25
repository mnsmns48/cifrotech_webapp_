from dataclasses import dataclass
from environs import Env


def transfer(s: str) -> tuple:
    _list = list()
    _list.append(s.split(',')[0])
    _list.append(int(s.split(',')[1]))
    return tuple(_list)


@dataclass
class RemotePGDb:
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
class LocalPGDb:
    local_db_user: str
    local_db_password: str
    local_db_host: str
    local_db_port: int
    local_db_name: str


@dataclass
class Settings:
    remote_pg_db: RemotePGDb
    local_pg_db: LocalPGDb


def load_config(path: str = None):
    env = Env()
    env.read_env()

    return Settings(
        remote_pg_db=RemotePGDb(
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
        local_pg_db=LocalPGDb(
            local_db_user=env.str("LOCAL_DB_USER"),
            local_db_password=env.str("LOCAL_DB_PASSWORD"),
            local_db_host=env.str("LOCAL_DB_HOST"),
            local_db_port=env.int("LOCAL_DB_PORT"),
            local_db_name=env.str("LOCAL_DB_NAME")
        )
    )


settings = load_config('..env')
