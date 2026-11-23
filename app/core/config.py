from typing import Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use the repo-root .env, resolved relative to the working directory
        # (the project is always run from the repo root).
        env_file=".env",
        env_ignore_empty=True,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    FASTAPI_ENV: Literal["development", "production"]
    PROJECT_NAME: str
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: PostgresDsn
    DATABASE_URL_LOCALHOST: PostgresDsn
    QUERY_TIMEOUT_SECONDS: int = 10

    @field_validator("DATABASE_URL", "DATABASE_URL_LOCALHOST", mode="before")
    @staticmethod
    def _use_psycopg_driver(value: str | PostgresDsn) -> str:
        database_url = str(value)
        for scheme in ("postgres://", "postgresql://"):
            if database_url.startswith(scheme):
                return database_url.replace(scheme, "postgresql+psycopg://", 1)
        return database_url


settings = Settings()
