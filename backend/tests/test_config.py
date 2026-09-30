"""Unit tests for configuration loading and validation."""

from app.core.config import Settings


def test_settings_default_values():
    """Verify default configuration values meet platform standards."""
    cfg = Settings()
    assert cfg.APP_NAME == "Customer Voice AI"
    assert cfg.API_V1_STR == "/api/v1"
    assert cfg.EMBEDDING_DIMENSION == 1536
    assert cfg.TREND_BASELINE_WEEKS == 4
    assert cfg.TREND_EMERGING_THRESHOLD_PCT == 25.0


def test_database_url_generation():
    """Verify synchronous and asynchronous database URLs format correctly."""
    cfg = Settings(
        POSTGRES_USER="testuser",
        POSTGRES_PASSWORD="testpassword",
        POSTGRES_SERVER="db.internal",
        POSTGRES_PORT=5432,
        POSTGRES_DB="testdb",
    )
    assert cfg.sync_database_url == "postgresql://testuser:testpassword@db.internal:5432/testdb"
    assert cfg.async_database_url == "postgresql+asyncpg://testuser:testpassword@db.internal:5432/testdb"


def test_cors_origins_configured():
    """Verify CORS origins include local frontend ports."""
    cfg = Settings()
    assert any("5173" in origin for origin in cfg.BACKEND_CORS_ORIGINS)
    assert any("3000" in origin for origin in cfg.BACKEND_CORS_ORIGINS)
