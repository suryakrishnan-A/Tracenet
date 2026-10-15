"""TraceNest Core Settings and Configuration."""

from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    PROJECT_NAME: str = "TraceNest API"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server Networking
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Cross-Origin Resource Sharing (CORS)
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Database Settings (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "tracenest"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tracenest"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tracenest_test"

    # AI Investigation Assistant Settings
    AI_PROVIDER: str = "openai_compatible"
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"
    AI_API_KEY: str = ""
    AI_REQUEST_TIMEOUT_SECONDS: int = 30
    AI_MAX_EVENTS_PER_INVESTIGATION: int = 5
    AI_MAX_STACK_TRACE_CHARS: int = 2000

    # Database Connection Pool Settings (Production)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_PRE_PING: bool = True

    # Rate Limiting & Security Settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_TELEMETRY_PER_MINUTE: int = 120
    RATE_LIMIT_INVESTIGATE_PER_MINUTE: int = 15
    MAX_REQUEST_SIZE_BYTES: int = 2 * 1024 * 1024  # 2 MB global limit
    WORKERS: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    from pydantic import model_validator

    @model_validator(mode="after")
    def validate_production_env(self):
        """Enforce strict production safeguards."""
        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                self.DEBUG = False
        return self


settings = Settings()
