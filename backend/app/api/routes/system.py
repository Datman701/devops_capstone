from datetime import datetime, timezone

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.config import settings
from app.database import engine

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """Liveness: is the process itself healthy? Deliberately does not touch the
    database, so a database outage cannot cause Kubernetes to kill the pod."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/api/health")
def api_health() -> dict:
    """Liveness alias under /api.

    In production only /api/* is routed to the backend by Nginx/Ingress, so the
    browser polls this path. The root /health stays probe-only for Kubernetes.
    """
    return health()


@router.get("/ready")
def ready(response: Response) -> dict:
    """Readiness: can this pod serve traffic right now? A connection pool that
    cannot reach PostgreSQL means the pod should be pulled from the Service."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report any DB failure as not-ready
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "unreachable", "detail": str(exc)}
    return {"status": "ready", "database": "ok"}


@router.get("/")
def root() -> dict:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "metrics": "/metrics",
    }


@router.get("/info", response_model=None)
def info() -> dict:
    return {"server_time": datetime.now(timezone.utc).isoformat()}
