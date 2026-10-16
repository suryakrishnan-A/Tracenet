"""TraceNest Core Settings and Configuration."""

from typing import List, Union
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


def normalize_database_url(url: str) -> str:
    """Normalize PostgreSQL connection string for SQLAlchemy asyncpg engine.

    Transforms:
    - postgres:// -> postgresql+asyncpg://
    - postgresql:// -> postgresql+asyncpg://
    - Maps sslmode=require to ssl=require for asyncpg compatibility
    - Strips unsupported asyncpg query parameters (e.g. channel_binding)
    - Preserves user, password, host, port, database, and compatible query params.
    """
    if not url:
        return url

    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()

    if scheme in ("postgres", "postgresql", "postgresql+psycopg2"):
        scheme = "postgresql+asyncpg"

    query_params = parse_qs(parsed.query, keep_blank_values=True)
    cleaned_params = {}

    for key, values in query_params.items():
        key_lower = key.lower()
        val = values[-1] if values else ""

        if key_lower == "sslmode":
            val_lower = val.lower()
            if val_lower in ("require", "verify-ca", "verify-full", "prefer"):
                cleaned_params["ssl"] = "require"
        elif key_lower == "channel_binding":
            # asyncpg does not support channel_binding kwarg
            continue
        elif key_lower == "ssl":
            val_lower = val.lower()
            if val_lower in ("true", "1", "require"):
                cleaned_params["ssl"] = "require"
            elif val_lower not in ("false", "0", "disable"):
                cleaned_params["ssl"] = val
        else:
            cleaned_params[key] = val

    new_query = urlencode(cleaned_params)
    return urlunparse((
        scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment,
    ))


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
        origins = []
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        origins = [str(i).strip() for i in parsed if str(i).strip()]
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON format for BACKEND_CORS_ORIGINS: {exc}")
            else:
                origins = [i.strip() for i in v_str.split(",") if i.strip()]
        elif isinstance(v, list):
            origins = [str(i).strip() for i in v if str(i).strip()]
        else:
            raise ValueError("BACKEND_CORS_ORIGINS must be a valid JSON array or comma-separated string")

        cleaned = []
        for origin in origins:
            norm = origin.rstrip("/")
            if norm == "*":
                cleaned.append("*")
                continue
            if not (norm.startswith("http://") or norm.startswith("https://")):
                raise ValueError(f"Invalid origin '{origin}': must start with http:// or https://")
            parsed = urlparse(norm)
            if parsed.path or parsed.query or parsed.params or parsed.fragment:
                raise ValueError(f"Invalid origin '{origin}': origin cannot contain path, query, or fragment")
            cleaned.append(norm)
        return cleaned

    # Database Settings (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "tracenest"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tracenest"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tracenest_test"

    @field_validator("DATABASE_URL", "TEST_DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            return normalize_database_url(v)
        return v

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
    RATE_LIMIT_PROJECT_CREATE_PER_MINUTE: int = 10
    PROJECT_REGISTRATION_ENABLED: bool = True
    MAX_REQUEST_SIZE_BYTES: int = 2 * 1024 * 1024  # 2 MB global limit
    WORKERS: int = 1

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_production_env(self):
        """Enforce strict production safeguards."""
        if self.ENVIRONMENT.lower() == "production":
            if self.DEBUG:
                self.DEBUG = False
            # Check wildcard CORS with credentials
            if "*" in self.BACKEND_CORS_ORIGINS:
                raise ValueError("Wildcard '*' origin is prohibited in production when credentials are enabled.")
            # Check for insecure default passwords in production
            insecure_passwords = {
                "postgres",
                "password",
                "changethisinproductionsecuredsecret!",
                "admin",
                "root",
                "123456",
            }
            if self.POSTGRES_PASSWORD.lower() in insecure_passwords:
                raise ValueError("Insecure default database password detected in production configuration. Please configure a secure, unique password.")
            parsed_db = urlparse(self.DATABASE_URL)
            if parsed_db.password and parsed_db.password.lower() in insecure_passwords:
                raise ValueError("Insecure default database password detected in DATABASE_URL during production deployment.")
        return self


settings = Settings()
