"""Application configuration using Pydantic Settings.

Supports loading from environment variables and .env files.
"""

from typing import List, Optional, Union
import json
import os

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field, field_validator
    _USE_PYDANTIC_SETTINGS = True
except ImportError:
    try:
        from pydantic import BaseSettings, Field, validator as field_validator  # type: ignore
        _USE_PYDANTIC_SETTINGS = False
    except ImportError:
        # Minimal pure Python fallback for baseline initialization before pip install
        class BaseSettings:  # type: ignore
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        Field = lambda default=None, **kwargs: default  # type: ignore
        field_validator = lambda *args, **kwargs: lambda f: f  # type: ignore
        _USE_PYDANTIC_SETTINGS = False


class Settings(BaseSettings):
    """Global application settings and environment variables."""

    # Application
    APP_NAME: str = "Customer Voice AI"
    ORGANIZATION_NAME: str = "Capital One"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "insecure-secret-key-for-development-only-change-me"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Database (PostgreSQL + pgvector)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "customervoice"
    POSTGRES_PASSWORD: str = "customervoice_secret"
    POSTGRES_DB: str = "customer_voice_ai"
    POSTGRES_POOL_SIZE: int = 10
    DATABASE_URL: Optional[str] = "sqlite+aiosqlite:///./cva_dev.db"

    # Kafka Messaging
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "customer-voice-ai-workers"
    KAFKA_ENABLE_FALLBACK_SYNC: bool = True
    KAFKA_TOPIC_REVIEW_CREATED: str = "review.created"
    KAFKA_TOPIC_REVIEW_ANALYZED: str = "review.analyzed"
    KAFKA_TOPIC_REVIEW_EMBEDDED: str = "review.embedded"
    KAFKA_TOPIC_ISSUE_DETECTED: str = "issue.detected"
    KAFKA_TOPIC_REPORT_GENERATED: str = "report.generated"

    # AI / LLM
    LLM_PROVIDER: str = "mock"  # "mock", "openai"
    OPENAI_API_KEY: str = "mock-api-key"
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024

    # Embeddings
    EMBEDDING_PROVIDER: str = "mock"  # "mock", "openai", "sentence-transformers"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536

    # Clustering & Trend Detection
    CLUSTERING_MIN_SAMPLES: int = 5
    CLUSTERING_EPS: float = 0.35
    TREND_BASELINE_WEEKS: int = 4
    TREND_EMERGING_THRESHOLD_PCT: float = 25.0

    @property
    def sync_database_url(self) -> str:
        """Construct synchronous SQLAlchemy connection URL."""
        if self.DATABASE_URL:
            if self.POSTGRES_SERVER != "localhost" or self.POSTGRES_USER != "customervoice":
                return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            if "sqlite+aiosqlite" in self.DATABASE_URL:
                return self.DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def async_database_url(self) -> str:
        """Construct asynchronous connection URL."""
        if self.DATABASE_URL:
            if self.POSTGRES_SERVER != "localhost" or self.POSTGRES_USER != "customervoice":
                return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    if _USE_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore",
        )


settings = Settings()
