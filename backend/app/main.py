"""
NeoPilot Backend — FastAPI Application
Main entry point with lifespan events, middleware, and route mounting.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.db import init_db
from backend.app.api.session import router as session_router, init_services
from backend.app.api.websocket import router as ws_router

logger = structlog.get_logger(__name__)

# ─── App startup time ─────────────────────────────────────────────────────────
_start_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    global _start_time
    _start_time = time.time()

    # Initialize database
    logger.info("initializing_database", url=settings.database_url)
    await init_db()
    logger.info("database_initialized")

    # Initialize services (Claude client, session manager)
    logger.info("initializing_services", model=settings.claude_model.value)
    init_services()
    logger.info("services_initialized")

    logger.info(
        "neopilot_backend_started",
        host=settings.host,
        port=settings.port,
        claude_model=settings.claude_model.value,
        debug=settings.debug,
    )

    yield

    # Shutdown
    logger.info("neopilot_backend_shutting_down")


# ─── FastAPI App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="NeoPilot Backend",
    description=(
        "NeoPilot Teaching Engine API — Universal software teacher powered by Claude.\n\n"
        "## Endpoints\n"
        "- **POST /session/start** — Start a new teaching session\n"
        "- **POST /session/observe** — Send screenshot/text observation\n"
        "- **POST /session/action-result** — Report action execution result\n"
        "- **GET /session/{id}/status** — Get session status\n"
        "- **WS /session/stream** — Real-time WebSocket channel\n"
    ),
    version="2.0.0-alpha",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request Logging Middleware ───────────────────────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every HTTP request with timing."""
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = (time.monotonic() - start) * 1000

    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        elapsed_ms=round(elapsed_ms, 1),
    )
    return response


# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(session_router)
app.include_router(ws_router)


# ─── Health & Info ────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "2.0.0-alpha",
        "claude_model": settings.claude_model.value,
        "database": "connected",
        "uptime_seconds": round(time.time() - _start_time, 1) if _start_time else 0,
    }


@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "NeoPilot Backend",
        "version": "2.0.0-alpha",
        "description": "Universal Software Teacher powered by Claude",
        "docs": "/docs",
        "health": "/health",
    }


# ─── Global Error Handler ────────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return 500."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )
