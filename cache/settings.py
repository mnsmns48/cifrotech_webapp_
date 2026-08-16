from pydantic_settings import BaseSettings


class CacheTTLSettings(BaseSettings):
    short: int
    medium: int
    long: int
    forever: int

    short_specs: int
    menu: int
    filters: int
    formula: int
    product_info: int

    class Config:
        env_prefix = "CACHE_TTL_"
        env_file = "./cache/.env"


cache_ttl = CacheTTLSettings()
