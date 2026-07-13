from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "分布式实时智能决策平台"
    database_url: str = "sqlite:///./platform.db"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    simulation_interval_seconds: float = 1.0
    simulation_autostart: bool = True
    kafka_bootstrap_servers: str = "localhost:9092"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

