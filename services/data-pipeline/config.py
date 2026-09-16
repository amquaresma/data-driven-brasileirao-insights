from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"

    supabase_url: str
    supabase_service_role_key: str

    highlightly_api_key: str
    highlightly_base_url: str = "https://soccer.highlightly.net"


@lru_cache
def get_settings() -> Settings:
    return Settings()
