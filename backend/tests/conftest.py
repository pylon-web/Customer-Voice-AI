"""Shared pytest fixtures for Customer Voice AI backend testing."""

import pytest
import asyncio
from typing import Generator
import os
import sys
from pathlib import Path

# Ensure workspace root and backend directory are in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Set testing environment prior to app loading
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["POSTGRES_SERVER"] = "localhost"
os.environ["POSTGRES_DB"] = "customer_voice_ai_test"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"

from fastapi.testclient import TestClient
from app.main import create_application
from app.core.database import init_db, async_session_factory
from app.repositories.team_repo import TeamRepository


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test tables and seed taxonomy once per test session."""
    async def _init():
        await init_db()
        async with async_session_factory() as session:
            repo = TeamRepository(session)
            await repo.seed_initial_taxonomy_if_empty()
            await session.commit()

    asyncio.run(_init())
    yield
    # Cleanup sqlite test db file if created
    test_db = Path("test_cva.db")
    if test_db.exists():
        try:
            test_db.unlink()
        except Exception:
            pass


@pytest.fixture(scope="session")
def app():
    """Create test application instance."""
    application = create_application()
    return application


@pytest.fixture(scope="session")
def client(app) -> Generator[TestClient, None, None]:
    """TestClient instance for making API requests."""
    with TestClient(app) as test_client:
        yield test_client
