from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = "postgresql+asyncpg://postgres:534534@localhost/activity_server"
    db_echo: bool = True


settings = Settings()
