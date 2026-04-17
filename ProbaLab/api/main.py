"""
ProbaLab API — FastAPI backend for football predictions.

Serves prediction data from Supabase to the React frontend.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from urllib.parse import urlparse as _urlparse

# APScheduler (worker.py) est la SOURCE DE VÉRITÉ du scheduling automatique.
# Les endpoints /api/trigger/* sont des déclenchements AD-HOC uniquement.
# Ne pas créer de crons Trigger.dev en double — leçon 64 NHL (2026-04-17).
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

# ─── Rate Limiting ──────────────────────────────────────────────
# Import limiter from shared module so routers can use the same instance
from api.rate_limit import RATE_LIMITING, limiter
from src.logging_config import generate_request_id, setup_logging

# Only import the exception handler when slowapi is available
if RATE_LIMITING:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

from api.response_models import HealthResponse
from api.routers import admin as admin_router
from api.routers import best_bets as best_bets_router
from api.routers import email as email_router
from api.routers import expert_picks as expert_picks_router
from api.routers import monitoring as monitoring_router
from api.routers import news as news_router
from api.routers import nhl, players, stripe_webhook, trigger
from api.routers import performance as performance_router
from api.routers import predictions as predictions_router
from api.routers import push as push_router
from api.routers import search as search_router
from api.routers import teams as teams_router
from api.routers import telegram as telegram_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance):
    """App lifespan — scheduling handled by Trigger.dev."""
    setup_logging()
    yield


tags_metadata = [
    {"name": "Health", "description": "Health check and status"},
    {"name": "Predictions", "description": "Football match predictions and detailed analysis"},
    {"name": "Best Bets", "description": "Paris du Soir — curated daily betting recommendations"},
    {"name": "Expert Picks", "description": "Expert manual picks with performance tracking"},
    {"name": "Performance", "description": "Historical accuracy and calibration metrics"},
    {"name": "Monitoring", "description": "CLV, Brier scores, and data quality health"},
    {"name": "Teams", "description": "Team history, roster, and meta-analysis"},
    {"name": "News", "description": "Sports news aggregation from RSS feeds"},
    {"name": "Search", "description": "Semantic search across predictions"},
    {"name": "Email", "description": "Transactional emails via Resend"},
    {"name": "Admin", "description": "Pipeline control and administration"},
    {"name": "NHL", "description": "NHL predictions and analysis"},
    {"name": "Stripe", "description": "Payment webhooks"},
    {"name": "Telegram", "description": "Telegram bot webhooks"},
    {"name": "Players", "description": "Player statistics and details"},
    {"name": "Push", "description": "Web push notifications"},
    {"name": "Trigger", "description": "Trigger.dev scheduled job endpoints"},
]

app = FastAPI(
    title="ProbaLab API",
    description="API de predictions sportives avec value betting. Football (8 ligues) + NHL.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# ─── Prometheus Instrumentation ──────────────────────────────────
# Exposes /metrics with automatic HTTP request counters, histograms,
# and size metrics for every route.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# ─── Rate Limiting ──────────────────────────────────────────────
if RATE_LIMITING:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Router Includes ─────────────────────────────────────────────
app.include_router(stripe_webhook.router)
app.include_router(nhl.router)
app.include_router(trigger.router)
app.include_router(telegram_router.router)
app.include_router(push_router.router)
app.include_router(players.router, prefix="/api/players", tags=["Players"])
app.include_router(admin_router.router)
app.include_router(best_bets_router.router)
app.include_router(email_router.router)
app.include_router(expert_picks_router.router)
app.include_router(monitoring_router.router)
app.include_router(news_router.router)
app.include_router(performance_router.router)
app.include_router(predictions_router.router)
app.include_router(search_router.router)
app.include_router(teams_router.router)

# ─── CORS Middleware ─────────────────────────────────────────────

_raw_origins = os.getenv("ALLOWED_ORIGINS", "")
if not _raw_origins:
    logger.warning("ALLOWED_ORIGINS not set — falling back to localhost dev origins")
    _raw_origins = "http://localhost:5173,http://localhost:4173"

origins = []
for _o in _raw_origins.split(","):
    _o = _o.strip()
    _parsed = _urlparse(_o)
    if _parsed.scheme in ("http", "https") and _parsed.netloc:
        origins.append(_o)
    elif _o:
        logger.warning("Ignoring invalid CORS origin: %s", _o)

if not origins:
    origins = ["http://localhost:5173", "http://localhost:4173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "stripe-signature"],
    allow_credentials=True,
)

# ─── Security Headers Middleware ────────────────────────────────
# Added AFTER CORSMiddleware in code = executes BEFORE it at runtime
# (Starlette middleware stack is LIFO)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ─── Request ID Middleware ───────────────────────────────────────
# Added last in code = executes first at runtime (Starlette LIFO stack)
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Generate a unique request ID for each incoming request and attach it
    to the response as X-Request-ID for traceability."""
    rid = generate_request_id()
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response


# ─── Global Exception Handler ────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler: log full traceback server-side, return generic 500 to client."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ─── Health Check ────────────────────────────────────────────────


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check with dependency status",
    response_model=HealthResponse,
)
async def health_check():
    """Health check endpoint for Railway / monitoring.

    Performs lightweight dependency probes (Supabase, Gemini) and returns
    an overall status of ``ok`` or ``degraded``.
    """
    from src.config import supabase as _supabase

    checks: dict[str, str] = {"api": "ok"}

    # Supabase connectivity probe
    try:
        _supabase.table("predictions").select("fixture_id").limit(1).execute()
        checks["supabase"] = "ok"
    except Exception:
        checks["supabase"] = "degraded"

    # Gemini client availability probe (no network call — just client init)
    try:
        from src.ai_service import get_gemini_client

        client = get_gemini_client()
        checks["gemini"] = "ok" if client else "unavailable"
    except Exception:
        checks["gemini"] = "unavailable"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
    }
