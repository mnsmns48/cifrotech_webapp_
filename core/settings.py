from pydantic.v1 import BaseSettings


class CoreConfig(BaseSettings):
    db_url: str = "postgresql+asyncpg://postgres:534534@localhost:5433/activity_server"
    db_echo: bool = True


core_config = CoreConfig()
