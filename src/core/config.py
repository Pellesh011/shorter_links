"""Application configuration settings."""

from pathlib import Path
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    database_url: str = "url_shortener.db"

    # Application
    app_title: str = "URL Shortener Service"
    app_version: str = "0.1.0"
    app_description: str = "A simple and lightweight URL shortening service"

    # URL Shortener
    default_short_code_length: int = 6
    max_short_code_length: int = 20
    min_short_code_length: int = 3

    @property
    def db_path(self) -> Path:
        """Get database path as Path object."""
        return Path(self.database_url)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

