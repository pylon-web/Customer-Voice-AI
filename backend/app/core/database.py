"""Asynchronous database engine, session management, and pgvector type adaptation."""

import json
from typing import AsyncGenerator, List, Optional
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("cva.database")


class VectorType(TypeDecorator):
    """Adaptive Vector type.

    Uses `pgvector.sqlalchemy.Vector` when targeting PostgreSQL,
    and falls back to JSON-serialized TEXT on SQLite for hermetic unit testing.
    """

    impl = TEXT
    cache_ok = True

    def __init__(self, dimension: int = 1536, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dimension = dimension

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            try:
                from pgvector.sqlalchemy import Vector
                return dialect.type_descriptor(Vector(self.dimension))
            except ImportError:
                return dialect.type_descriptor(TEXT())
        return dialect.type_descriptor(TEXT())

    def process_bind_param(self, value: Optional[List[float]], dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect) -> Optional[List[float]]:
        if value is None:
            return None
        if isinstance(value, list):
            return value
        if dialect.name == "postgresql":
            try:
                import numpy as np
                if isinstance(value, np.ndarray):
                    return value.tolist()
            except ImportError:
                pass
            return list(value)
        return json.loads(value)


# Create Async Engine
def get_engine_url() -> str:
    """Determine database connection URL based on active environment."""
    if settings.ENVIRONMENT == "test":
        return "sqlite+aiosqlite:///:memory:"
    return settings.async_database_url


engine = create_async_engine(
    get_engine_url(),
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Async Session Factory
async_session_factory = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session with automatic cleanup."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db(engine_instance=None) -> None:
    """Initialize database schemas, extensions, and default taxonomy seeds."""
    active_engine = engine_instance or engine
    async with active_engine.begin() as conn:
        # If PostgreSQL, enable pgvector extension
        if active_engine.dialect.name == "postgresql":
            logger.info("Ensuring pgvector extension is enabled in PostgreSQL")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

        # Import models so metadata is populated
        from app.models.entities import Base
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized successfully")
