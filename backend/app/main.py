"""FastAPI application entry point."""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import admin, agent, auth, chat, chat_history, court_cases, dashboard, documents, lawyers, news, payments, templates

logger = structlog.get_logger(__name__)

settings = get_settings()

# ──────────────────────────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "AI Lawyer — Bangladesh Legal API",
    description = "AI-powered Bangladesh law assistant (CLAUDE.md §1)",
    version     = "0.1.0",
    docs_url    = "/docs" if settings.DEBUG else None,
    redoc_url   = "/redoc" if settings.DEBUG else None,
)

# ──────────────────────────────────────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────────────────────────
# Global exception handler — never leak stack traces in production
# ──────────────────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

# ──────────────────────────────────────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────────────────────────────────────

app.include_router(auth.router,      prefix="/api")
app.include_router(chat.router,      prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(payments.router,  prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(lawyers.router,      prefix="/api")
app.include_router(court_cases.router,  prefix="/api")
app.include_router(chat_history.router, prefix="/api")
app.include_router(admin.router,       prefix="/api")
app.include_router(templates.router,   prefix="/api")
app.include_router(news.router,        prefix="/api")
app.include_router(agent.router,       prefix="/api")

# ──────────────────────────────────────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["infra"])
async def health() -> dict:
    return {"status": "ok", "version": app.version}
