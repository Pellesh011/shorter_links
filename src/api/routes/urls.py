"""URL shortening API routes.

This module contains all endpoints for URL operations:
- Create short URL (POST /shorten)
- Redirect to original URL (GET /{short_code})
- Update URL (PUT /{short_code})
- Delete URL (DELETE /{short_code})
- Get URL info (GET /{short_code}/info)
- List all URLs (GET /)
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse

from ...core.database import Database, get_db
from ...models.url import URLCreate, ErrorResponse
from ...schemas.url import (
    URLCreateResponse,
    URLInfoResponse,
    URLDeleteResponse,
)
from ...utils.shortener import (
    generate_short_code,
    validate_short_code,
    normalize_url,
    create_short_url,
)

router = APIRouter(prefix="", tags=["URLs"])


def get_base_url(request: Request) -> str:
    """Get base URL from request.

    Args:
        request: FastAPI request object.

    Returns:
        Base URL string.
    """
    return str(request.base_url).rstrip("/")


@router.post(
    "/shorten",
    response_model=URLCreateResponse,
    status_code=201,
    responses={
        201: {"description": "Short URL created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        409: {"model": ErrorResponse, "description": "Short code already exists"},
    },
    summary="Create a short URL",
    description="Create a new short URL from a long URL. Optionally specify a custom code.",
)
async def create_short_url_endpoint(
    request: Request,
    url_data: URLCreate,
    db: Database = Depends(get_db),
) -> URLCreateResponse:
    """Create a short URL from a long URL.

    Args:
        request: FastAPI request object.
        url_data: URL creation data.
        db: Database instance.

    Returns:
        Created URL information.
    """
    # Normalize and validate the original URL
    original_url = normalize_url(str(url_data.original_url))

    # Handle custom code or generate new one
    short_code: str
    if url_data.custom_code:
        if not validate_short_code(url_data.custom_code):
            raise HTTPException(
                status_code=400,
                detail="Custom code must be 3-20 alphanumeric characters",
            )
        if db.url_exists(url_data.custom_code):
            raise HTTPException(
                status_code=409, detail="Short code already exists"
            )
        short_code = url_data.custom_code
    else:
        # Generate unique short code
        max_attempts = 10
        for _ in range(max_attempts):
            short_code = generate_short_code()
            if not db.url_exists(short_code):
                break
        else:
            raise HTTPException(
                status_code=500, detail="Failed to generate unique short code"
            )

    # Handle expiration
    expires_at = url_data.expires_at.isoformat() if url_data.expires_at else None

    # Create URL in database
    url_record = db.create_url(original_url, short_code, expires_at)

    # Build response
    base_url = get_base_url(request)
    short_url = create_short_url(base_url, short_code)

    return URLCreateResponse(
        original_url=original_url,
        short_code=short_code,
        short_url=short_url,
        created_at=url_record["created_at"],
        expires_at=url_record["expires_at"],
    )


@router.get(
    "/{short_code}",
    response_class=RedirectResponse,
    status_code=302,
    responses={
        302: {"description": "Redirect to original URL"},
        404: {"model": ErrorResponse, "description": "Short URL not found"},
    },
    summary="Redirect to original URL",
    description="Redirect to the original URL associated with the short code.",
)
async def redirect_to_url(
    short_code: str,
    db: Database = Depends(get_db),
) -> RedirectResponse:
    """Redirect to the original URL.

    Args:
        short_code: The short URL code.
        db: Database instance.

    Returns:
        Redirect response to original URL.
    """
    # Validate short code format
    if not validate_short_code(short_code):
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Get URL from database
    url_record = db.get_url_by_code(short_code)

    if not url_record:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Increment click count
    db.increment_clicks(short_code)

    # Return redirect response
    return RedirectResponse(
        url=url_record["original_url"], status_code=302
    )


@router.delete(
    "/{short_code}",
    response_model=URLDeleteResponse,
    responses={
        200: {"description": "URL deleted successfully"},
        404: {"model": ErrorResponse, "description": "Short URL not found"},
    },
    summary="Delete a short URL",
    description="Soft delete a short URL (mark as inactive).",
)
async def delete_short_url(
    short_code: str,
    db: Database = Depends(get_db),
) -> dict:
    """Delete a short URL.

    Args:
        short_code: The short URL code.
        db: Database instance.

    Returns:
        Deletion confirmation.
    """
    # Validate short code format
    if not validate_short_code(short_code):
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Delete URL from database
    deleted = db.delete_url(short_code)

    if not deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return {
        "message": "URL deleted successfully",
        "short_code": short_code,
    }


@router.put(
    "/{short_code}",
    response_model=URLInfoResponse,
    responses={
        200: {"description": "URL updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Short URL not found"},
    },
    summary="Update a short URL",
    description="Update the original URL associated with a short code.",
)
async def update_short_url(
    short_code: str,
    request: Request,
    url_data: URLCreate,
    db: Database = Depends(get_db),
) -> dict:
    """Update a short URL.

    Args:
        short_code: The short URL code.
        request: FastAPI request object.
        url_data: URL update data.
        db: Database instance.

    Returns:
        Updated URL information.
    """
    # Validate short code format
    if not validate_short_code(short_code):
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Check if URL exists
    existing_url = db.get_url_by_code(short_code)
    if not existing_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Normalize the new URL
    original_url = normalize_url(str(url_data.original_url))

    # Update URL in database
    url_record = db.update_url(short_code, original_url)

    # Build response
    base_url = get_base_url(request)
    short_url = create_short_url(base_url, short_code)

    return {
        "original_url": original_url,
        "short_code": short_code,
        "short_url": short_url,
        "created_at": url_record["created_at"],
        "expires_at": url_record["expires_at"],
        "clicks": url_record["clicks"],
        "is_active": url_record["is_active"],
    }


@router.get(
    "/{short_code}/info",
    response_model=URLInfoResponse,
    responses={
        200: {"description": "URL information retrieved"},
        404: {"model": ErrorResponse, "description": "Short URL not found"},
    },
    summary="Get URL information",
    description="Get information about a short URL.",
)
async def get_url_info(
    short_code: str,
    request: Request,
    db: Database = Depends(get_db),
) -> dict:
    """Get URL information.

    Args:
        short_code: The short URL code.
        request: FastAPI request object.
        db: Database instance.

    Returns:
        URL information.
    """
    # Validate short code format
    if not validate_short_code(short_code):
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Get URL from database
    url_record = db.get_url_by_code(short_code)

    if not url_record:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Build response
    base_url = get_base_url(request)
    short_url = create_short_url(base_url, short_code)

    return {
        "original_url": url_record["original_url"],
        "short_code": short_code,
        "short_url": short_url,
        "created_at": url_record["created_at"],
        "expires_at": url_record["expires_at"],
        "clicks": url_record["clicks"],
        "is_active": bool(url_record["is_active"]),
    }


@router.get(
    "/",
    response_model=list[URLInfoResponse],
    summary="List all URLs",
    description="List all active short URLs.",
)
async def list_urls(
    request: Request,
    db: Database = Depends(get_db),
) -> list[dict]:
    """List all active URLs.

    Args:
        request: FastAPI request object.
        db: Database instance.

    Returns:
        List of URL information.
    """
    # Get all URLs from database
    urls = db.get_all_urls()

    # Build response
    base_url = get_base_url(request)
    result = []
    for url in urls:
        short_url = create_short_url(base_url, url["short_code"])
        result.append(
            {
                "original_url": url["original_url"],
                "short_code": url["short_code"],
                "short_url": short_url,
                "created_at": url["created_at"],
                "expires_at": url["expires_at"],
                "clicks": url["clicks"],
                "is_active": bool(url["is_active"]),
            }
        )

    return result

