"""URL Shortener Service - Main FastAPI Application.

A simple and lightweight URL shortening service with:
- Create short URLs
- Redirect to original URLs
- Delete URLs
- Update URLs
- Custom short codes
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.database import get_db
from .api.routes import health_router, urls_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.app_title}...")
    db = get_db()
    db.init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down URL Shortener Service...")
    db.close()


# Create FastAPI application
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler."""
    logger.error(f"Unhandled Exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "500"},
    )


# Include routers
app.include_router(health_router)
app.include_router(urls_router)

