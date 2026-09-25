"""
humana/app/main.py
FastAPI application factory and lifespan manager.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api import customers, health, knowledge, websocket
from app.core.config import get_settings
from app.core.database import create_tables
from app.core.logging import get_logger, setup_logging

setup_logging()
log = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    log.info("humana_startup", env=settings.app_env, port=settings.app_port)
    await create_tables()
    log.info("db_tables_ready")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    log.info("humana_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="HUMANA Platform API",
        description=(
            "Multi-tenant AI avatar backend. "
            "Provides customer management, knowledge base ingestion, "
            "WebSocket avatar conversations with RAG + LLM + TTS pipeline."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(customers.router)
    app.include_router(knowledge.router)
    app.include_router(health.router)
    app.include_router(websocket.router)

    # ── Root ──────────────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": "HUMANA Platform API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.is_dev,
        log_level="debug" if settings.is_dev else "info",
    )
