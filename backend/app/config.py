from functools import lru_cache
from typing import List

from pydantic import AnyUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_lawyer"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # AI
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Auth
    NEXTAUTH_SECRET: str = "change-me-in-production"
    JWT_SECRET: str = "change-me"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "ai-lawyer-docs"

    # Monitoring
    SENTRY_DSN: str = ""

    # SSLCommerz payment gateway
    SSLCOMMERZ_STORE_ID:       str  = "testbox"
    SSLCOMMERZ_STORE_PASSWORD: str  = "qwerty"
    SSLCOMMERZ_SANDBOX:        bool = True

    # Public URLs (used for SSLCommerz callback construction)
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL:  str = "http://localhost:8000"

    # App
    DEBUG: bool = False
    ENVIRONMENT: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
