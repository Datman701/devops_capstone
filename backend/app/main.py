from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from app.api.routes import appointments, directory, stats, system
from app.config import settings
from app.database import engine

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("clinicdesk")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    logger.info(
        "Starting %s v%s (env=%s)",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )
    yield
    engine.dispose()
    logger.info("Shutdown complete, connection pool closed")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "ClinicDesk appointment booking API. Manage doctors, patients and "
        "appointments with slot-conflict protection."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # The frontend is served from a different origin in dev (Vite on :5173).
    allow_origins=["*"] if settings.app_env == "development" else [],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(system.router)
app.include_router(directory.router)
app.include_router(stats.router)
app.include_router(appointments.router)

# Prometheus scraping endpoint used later by the ServiceMonitor in M9.
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    excluded_handlers=["/metrics"],
)
instrumentator.add(
    metrics.latency(
        metric_name="http_request_duration_seconds",
        metric_doc="Duration of HTTP requests in seconds",
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )
)
instrumentator.add(
    metrics.requests(
        metric_name="http_requests_total",
        metric_doc="Total number of requests by method, status and handler",
    )
)
instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=True)


@app.get("/livez", include_in_schema=False)
def livez() -> dict:
    """Alias kept for platforms that expect the Kubernetes-style probe path."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


__all__ = ["app"]
