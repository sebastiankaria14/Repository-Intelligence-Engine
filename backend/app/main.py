"""
Repository Intelligence Engine — FastAPI Application
Main application entry point with lifespan management.
"""

from __future__ import annotations

import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import get_logger, setup_logging
from app.api.health import router as health_router
from app.api.repositories import router as repositories_router
from app.api.websocket import router as websocket_router

# Initialize structured logging
setup_logging("DEBUG" if settings.debug else "INFO")
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — initialize and cleanup resources."""
    log.info("app_starting", app=settings.app_name)

    # Initialize PostgreSQL tables
    try:
        await init_db()
        log.info("postgres_initialized")
    except Exception as e:
        log.error("postgres_init_failed", error=str(e))

    yield

    # Cleanup
    log.info("app_shutting_down")


app = FastAPI(
    title="Repository Intelligence Engine",
    description="AI-powered software intelligence platform — an MRI for your codebase.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
cors_origins = list(dict.fromkeys(settings.backend_cors_origins + [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(repositories_router, prefix="/api")
app.include_router(websocket_router)


@app.get("/")
async def root():
    return {
        "name": "Repository Intelligence Engine",
        "version": "0.1.0",
        "docs": "/docs",
    }
