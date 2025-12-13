"""FastAPI application entry point."""

import logging
import time
import uuid

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy import text

from app.api.v1.router import router as api_router
from app.core.config import settings
from app.core.logging import request_id_var, setup_logging
from app.db.session import async_session

# Configure structured logging
setup_logging(debug=settings.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Sentry (must be before FastAPI app creation)
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        release=settings.VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,
    )
    logger.info("Sentry initialized (env=%s)", settings.SENTRY_ENVIRONMENT)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next) -> Response:
    """Add correlation ID and log request/response."""
    rid = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
    request_id_var.set(rid)

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)

    response.headers["X-Request-ID"] = rid

    logger.info(
        "%s %s → %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health/live")
async def liveness():
    """Liveness probe — confirms the process is running."""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    """Readiness probe — confirms DB and Redis are reachable."""
    checks: dict[str, str] = {}

    # Database check
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis check
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        r.close()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
        status_code=200 if all_ok else 503,
    )


@app.get("/health")
async def health_check():
    """Full health check — DB, Redis, version info."""
    checks: dict[str, str] = {}

    # Database check
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Redis check
    try:
        r = Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        r.close()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Celery check (best-effort, don't fail health on this)
    try:
        from app.workers.celery_app import celery_app as _celery

        inspect = _celery.control.inspect(timeout=2)
        ping_result = inspect.ping()
        checks["celery"] = "ok" if ping_result else "no workers"
    except Exception as e:
        checks["celery"] = f"error: {e}"

    # Celery is best-effort; only DB and Redis are critical
    critical = {k: v for k, v in checks.items() if k != "celery"}
    all_ok = all(v == "ok" for v in critical.values())
    return JSONResponse(
        content={
            "status": "healthy" if all_ok else "degraded",
            "version": settings.VERSION,
            "checks": checks,
        },
        status_code=200 if all_ok else 503,
    )


if settings.DEBUG:

    @app.get("/debug/sentry")
    async def trigger_sentry_error():
        """Test endpoint to verify Sentry integration (dev only)."""
        raise RuntimeError("Sentry test error")
