"""FastAPI application entrypoint for Customer Voice AI Backend."""

from contextlib import asynccontextmanager
import time
from typing import AsyncGenerator
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.errors import AppBaseException
from app.api.v1.api import api_router
from app.kafka.producer import get_kafka_producer

# Initialize structured logging
setup_logging(level=settings.LOG_LEVEL, environment=settings.ENVIRONMENT)
logger = get_logger("cva.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and graceful shutdown."""
    logger.info(
        "Starting Customer Voice AI service",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        llm_provider=settings.LLM_PROVIDER,
    )
    # Start Kafka Producer (connects to broker or initializes fallback mode)
    kafka_producer = get_kafka_producer()
    await kafka_producer.start()

    yield

    # Gracefully stop Kafka Producer
    await kafka_producer.stop()
    logger.info("Shutting down Customer Voice AI service gracefully")


def create_application() -> FastAPI:
    """Application factory configuring routes, middlewares, and error handlers."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-powered Customer Voice Intelligence Platform that ingests customer reviews, "
            "analyzes sentiment and issues, discovers semantic clusters, detects emerging trends, "
            "generates evidence-backed recommendations, routes to business teams, and compiles "
            "weekly executive intelligence reports."
        ),
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        lifespan=lifespan,
    )

    # Configure Cross-Origin Resource Sharing (CORS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_origin_regex=r"https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID and Request Timing Middleware
    @app.middleware("http")
    async def trace_and_timing_middleware(request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        response = await call_next(request)

        process_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)

        # Log request if not health probe
        if not request.url.path.endswith("/health"):
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({process_time_ms}ms)",
                extra={"correlation_id": correlation_id, "duration_ms": process_time_ms},
            )

        return response

    # Global Domain Exception Handler
    @app.exception_handler(AppBaseException)
    async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
        logger.warning(
            f"Domain exception on {request.url.path}: {exc.message}",
            extra={"status_code": exc.status_code, "details": exc.details},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "message": exc.message,
                    "status_code": exc.status_code,
                    "details": exc.details,
                }
            },
        )

    # Generic Unhandled Exception Handler
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Unhandled exception on {request.url.path}: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": "An unexpected internal server error occurred.",
                    "status_code": 500,
                }
            },
        )

    # Mount API v1 Master Router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    # Mount Static Frontend SPA if built
    frontend_dist = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    )
    assets_dir = os.path.join(frontend_dist, "assets")
    index_html = os.path.join(frontend_dist, "index.html")

    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", tags=["Root"])
    async def root(request: Request):
        """Root service metadata redirect or frontend dashboard."""
        accept = request.headers.get("accept", "")
        if "text/html" in accept and not accept.startswith("*/*") and os.path.exists(index_html):
            return FileResponse(index_html)
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "docs": f"{settings.API_V1_STR}/docs",
            "health": f"{settings.API_V1_STR}/health",
        }

    @app.get("/app", include_in_schema=False)
    @app.get("/dashboard", include_in_schema=False)
    async def serve_app():
        """Direct route to frontend SPA dashboard."""
        if os.path.exists(index_html):
            return FileResponse(index_html)
        return JSONResponse(
            status_code=404,
            content={"message": "Frontend build not found. Run 'npm run build' first."},
        )

    @app.get(
        "/metrics",
        response_class=PlainTextResponse,
        tags=["Observability"],
        include_in_schema=False,
    )
    async def metrics_root() -> PlainTextResponse:
        """Root Prometheus metrics scraper path."""
        from app.core.metrics import registry
        return PlainTextResponse(
            content=registry.render(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    return app


app = create_application()
