"""Health check, deep readiness probes, and Prometheus metrics endpoints."""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, status, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.metrics import registry, DB_PING_LATENCY_SECONDS
from app.kafka.producer import get_kafka_producer

router = APIRouter(tags=["Health & Observability"])


class HealthResponse(BaseModel):
    """Schema for basic liveness probe."""
    status: str
    app: str
    version: str
    environment: str
    timestamp: str


class DependencyStatus(BaseModel):
    """Schema for individual dependency health."""
    status: str
    latency_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class ReadinessResponse(BaseModel):
    """Schema for comprehensive readiness probe checking downstream dependencies."""
    status: str
    app: str
    version: str
    timestamp: str
    dependencies: Dict[str, Any]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Liveness Check",
    description="Returns HTTP 200 if the application process is running.",
)
@router.get(
    "/health/live",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Kubernetes Liveness Check",
    description="Dedicated Kubernetes liveness probe route.",
)
async def get_health() -> HealthResponse:
    """Liveness probe for Kubernetes and Docker."""
    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Deep Readiness Check",
    description="Verifies downstream services (PostgreSQL live ping, Kafka connectivity/fallback, AI model).",
)
async def get_readiness(response: Response) -> ReadinessResponse:
    """Readiness probe verifying live connectivity to PostgreSQL, Kafka, and LLM services."""
    deps: Dict[str, Any] = {}
    is_ready = True

    # 1. Live Database Ping (PostgreSQL / SQLite test)
    db_start = time.perf_counter()
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - db_start) * 1000, 2)
        DB_PING_LATENCY_SECONDS.set(db_latency / 1000.0)
        deps["database"] = {
            "status": "ready",
            "latency_ms": db_latency,
            "engine": "postgresql" if settings.ENVIRONMENT != "test" else "sqlite_memory",
        }
    except Exception as db_err:
        is_ready = False
        deps["database"] = {
            "status": "unhealthy",
            "error": str(db_err),
        }

    # 2. Kafka Message Broker / Fallback Status
    try:
        kafka_producer = get_kafka_producer()
        is_kafka_connected = kafka_producer.is_connected
        queue_size = kafka_producer.fallback_queue.qsize()
        fallback_active = not is_kafka_connected and kafka_producer.fallback_enabled

        deps["kafka"] = {
            "status": "ready" if (is_kafka_connected or fallback_active) else "degraded",
            "connected_to_broker": is_kafka_connected,
            "fallback_mode_active": fallback_active,
            "fallback_buffered_messages": queue_size,
        }
    except Exception as k_err:
        deps["kafka"] = {
            "status": "unhealthy",
            "error": str(k_err),
        }

    # 3. LLM / AI Configuration
    deps["llm_provider"] = {
        "status": "ready",
        "provider": settings.LLM_PROVIDER,
        "model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    }

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_ready else "unhealthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=deps,
    )


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    summary="Prometheus Metrics Scrape Endpoint",
    description="Exposes application telemetry in Prometheus plain-text 0.0.4 exposition format.",
)
async def get_metrics() -> PlainTextResponse:
    """Export Prometheus format metrics."""
    return PlainTextResponse(
        content=registry.render(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
