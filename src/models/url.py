"""Pydantic models for URL Shortener Service."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class URLCreate(BaseModel):
    """Model for creating a short URL."""

    original_url: HttpUrl = Field(..., description="The original long URL to shorten")
    custom_code: Optional[str] = Field(
        None, min_length=3, max_length=20, description="Custom short code"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Expiration timestamp"
    )


class URLInfo(BaseModel):
    """Model for URL information."""

    id: int
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks: int = 0
    is_active: bool = True


class ErrorResponse(BaseModel):
    """Model for error responses."""

    detail: str
    error_code: Optional[str] = None

