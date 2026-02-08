"""API routes package for URL Shortener Service."""

from .health import router as health_router
from .urls import router as urls_router

__all__ = ["health_router", "urls_router"]

