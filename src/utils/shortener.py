"""URL shortening utilities module.

This module handles the generation and validation of short codes.
"""

import random
import string
import re
from typing import Optional
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


# Characters allowed in short codes
ALPHABET = string.ascii_letters + string.digits


def generate_short_code(length: Optional[int] = None) -> str:
    """Generate a random short code.

    Args:
        length: Length of the generated code. Defaults to settings value.

    Returns:
        Random short code string.
    """
    length = length or settings.default_short_code_length
    return "".join(random.choices(ALPHABET, k=length))


def validate_short_code(code: str) -> bool:
    """Validate short code format.

    Args:
        code: Short code to validate.

    Returns:
        True if valid, False otherwise.
    """
    if not code:
        return False
    if len(code) < settings.min_short_code_length or len(code) > settings.max_short_code_length:
        return False
    if not re.match(r"^[a-zA-Z0-9]+$", code):
        return False
    return True


def normalize_url(url: str) -> str:
    """Normalize URL by stripping whitespace and ensuring http/https prefix.

    Args:
        url: URL to normalize.

    Returns:
        Normalized URL string.
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def is_url_expired(expires_at: Optional[str]) -> bool:
    """Check if URL has expired.

    Args:
        expires_at: Expiration timestamp string.

    Returns:
        True if expired, False otherwise.
    """
    from datetime import datetime

    if not expires_at:
        return False
    try:
        expire_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(expire_time.tzinfo) > expire_time
    except (ValueError, AttributeError):
        return False


def create_short_url(base_url: str, short_code: str) -> str:
    """Create full short URL from base URL and short code.

    Args:
        base_url: Base URL of the service.
        short_code: Short code.

    Returns:
        Full short URL string.
    """
    return f"{base_url.rstrip('/')}/{short_code}"


def extract_original_url(full_url: str) -> str:
    """Extract original URL from full short URL.

    Args:
        full_url: Full short URL.

    Returns:
        Original URL string.
    """
    # Remove trailing slash and get the last segment
    parts = full_url.rstrip("/").split("/")
    if parts:
        return "/".join(parts[:-1])
    return full_url

