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
    auth_secret: str = "change-this-secret-before-production"
    auth_access_token_minutes: int = 1440
    smtp_host: str | None = None
    smtp_port: int = 465
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = False
    email_code_expire_minutes: int = 10
    email_code_resend_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

