"""Pydantic models for URL Shortener Service."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class URLCreate(BaseModel):
    """Model for creating a short URL."""

    original_url: HttpUrl = Field(..., description="The original long URL to shorten")
    custom_code: Optional[str] = Field(
        None, min_length=3, max_length=20, description="Custom short code"
    )
    expires_at: Optional[datetime] = Field(
        None, description="Expiration timestamp"
    )


class URLCreateResponse(BaseModel):
    """Response model for created short URL."""

    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class URLInfo(BaseModel):
    """Model for URL information."""

    id: int
    original_url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks: int = 0
    is_active: bool = True


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


class ErrorResponse(BaseModel):
    """Model for error responses."""

    detail: str
    error_code: Optional[str] = None


class RedirectResponse(BaseModel):
    """Response model for redirect."""

    original_url: str
    short_code: str

