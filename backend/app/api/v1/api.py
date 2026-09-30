from fastapi import APIRouter
from app.api.v1 import health, reviews, clusters, trends, investigations, routing, reports, analytics

api_router = APIRouter()

# Core health routes
api_router.include_router(health.router)

# Analytics and catalog routes
api_router.include_router(analytics.router)

# Review ingestion and search routes
api_router.include_router(reviews.router)

# Issue clustering routes
api_router.include_router(clusters.router)

# Trend and velocity anomaly routes
api_router.include_router(trends.router)

# Root cause investigation and HITL recommendation routes
api_router.include_router(investigations.router)

# Team management and configurable routing engine
api_router.include_router(routing.router)

# Weekly Executive Intelligence Reports
api_router.include_router(reports.router)




