"""Application configuration using Pydantic Settings."""

import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "Marketing Mix Model API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Debug
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mmm"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # JWT Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File Upload Settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS: list[str] = [".csv", ".xlsx", ".xls"]

    # Sentry
    SENTRY_DSN: str | None = None
    SENTRY_ENVIRONMENT: str = "development"
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1

    # Email Settings (Resend)
    RESEND_API_KEY: str | None = None
    EMAIL_FROM: str = "noreply@example.com"
    EMAIL_FROM_NAME: str = "Marketing Mix Model"

    # Password Reset
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24
    FRONTEND_URL: str = "http://localhost:3000"

    @model_validator(mode="after")
    def _validate_secret_key(self) -> "Settings":
        default_key = "your-secret-key-change-in-production"
        if self.SECRET_KEY == default_key:
            if not self.DEBUG:
                raise ValueError("SECRET_KEY must be changed from the default value in production (DEBUG=False).")
            warnings.warn(
                "Using default SECRET_KEY. Set a secure key before deploying.",
                UserWarning,
                stacklevel=2,
            )
        return self

    @property
    def async_database_url(self) -> str:
        """Get async database URL."""
        return self.DATABASE_URL


settings = Settings()
