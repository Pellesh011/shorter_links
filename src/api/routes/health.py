"""Health check API routes."""

from fastapi import APIRouter
from ...schemas.url import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status.
    """
    return {"status": "healthy"}

