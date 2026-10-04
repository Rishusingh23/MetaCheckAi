from typing import List, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized Application Settings.
    Loaded from environment variables or .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "MetaCheck AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # CORS Configuration
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Authentication & Security
    JWT_SECRET: str = "metacheck-super-secret-jwt-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours
    JWT_ISSUER: str = "metacheck-ai"
    JWT_AUDIENCE: str = "metacheck-enforcement"
    DEMO_SEED_ENABLED: bool = False  # Set to False in production environments (true in demo)
    DEMO_DATA_ENABLED: bool = False  # Set to False in production; enable explicitly in SIH Demo environment
    UPLOAD_MAX_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads"
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    OCR_ENGINE: str = "AUTO"
    STORAGE_PROVIDER: str = "LOCAL"

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "metacheck_user"
    POSTGRES_PASSWORD: str = "metacheck_secure_password_replace_me"
    POSTGRES_DB: str = "metacheck_db"
    DATABASE_URL: str = ""
    DATABASE_SYNC_URL: str = ""

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """
        Fail fast in production/staging/sih environments if an insecure or default JWT_SECRET is configured.
        """
        env = (self.ENVIRONMENT or "development").lower().strip()
        if env in ["production", "staging", "sih", "prod"]:
            insecure_defaults = [
                "metacheck-super-secret-jwt-key-change-in-production-2026",
                "metacheck_default_secret_key_change_in_production",
                "secret",
                "changeme",
                "jwt_secret",
                "default_secret",
            ]
            secret = (self.JWT_SECRET or "").strip()
            if (
                not secret
                or secret in insecure_defaults
                or len(secret) < 32
                or "change-in-production" in secret.lower()
            ):
                raise ValueError(
                    f"Insecure or default JWT_SECRET is not permitted in '{env}' environment. "
                    "An explicit, cryptographically secure secret (at least 32 characters) must be configured via the JWT_SECRET environment variable."
                )
        return self

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    def get_sync_database_url(self) -> str:
        if self.DATABASE_SYNC_URL:
            return self.DATABASE_SYNC_URL
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
