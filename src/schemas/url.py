"""Response schemas for URL Shortener Service."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class URLCreateResponse(BaseModel):
    """Response model for created short URL."""

    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class URLInfoResponse(BaseModel):
    """Response model for URL info."""

    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks: int
    is_active: bool


class URLDeleteResponse(BaseModel):
    """Response model for URL deletion."""

    message: str
    short_code: str


class RedirectResponse(BaseModel):
    """Response model for redirect."""

    original_url: str
    short_code: str


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str

