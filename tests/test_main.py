"""Tests for URL Shortener Service."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import app
from src.core.database import Database
from src.utils.shortener import generate_short_code, validate_short_code, normalize_url


@pytest.fixture
def test_db():
    """Create a test database instance."""
    db = Database(":memory:")
    db.init_db()
    yield db
    db.close()


@pytest.fixture
def client(test_db):
    """Create a test client with mocked database."""
    from src.core.database import get_db
    
    # Set the dependency override BEFORE creating TestClient
    # so endpoint requests use the test database
    app.dependency_overrides[get_db] = lambda: test_db
    
    # Manually manage the app lifecycle to avoid the default lifespan
    # which would use the global database
    from contextlib import asynccontextmanager
    
    # Store original lifespan
    original_lifespan = app.router.lifespan_context
    
    # Override lifespan to not initialize database (we use test_db directly)
    @asynccontextmanager
    async def test_lifespan(app):
        yield
    
    app.router.lifespan_context = test_lifespan
    
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    
    # Restore original lifespan
    app.router.lifespan_context = original_lifespan
    app.dependency_overrides.clear()


@pytest.fixture
def mock_db():
    """Create a mock database."""
    return MagicMock(spec=Database)


class TestShortenerLogic:
    """Tests for URL shortening logic functions."""

    def test_generate_short_code_length(self):
        """Test that generated short codes have correct length."""
        for length in [4, 6, 8, 10]:
            code = generate_short_code(length)
            assert len(code) == length

    def test_generate_short_code_alphanumeric(self):
        """Test that generated codes are alphanumeric."""
        for _ in range(100):
            code = generate_short_code()
            assert code.isalnum()

    def test_validate_short_code_valid(self):
        """Test validation of valid short codes."""
        valid_codes = ["abc", "abc123", "Abc123", "a1b2c3", "shortcode"]
        for code in valid_codes:
            assert validate_short_code(code) is True

    def test_validate_short_code_invalid(self):
        """Test validation of invalid short codes."""
        invalid_codes = [
            "",
            "ab",  # too short
            "a" * 25,  # too long
            "abc@123",  # special chars
            "abc def",  # spaces
            "abc-123",  # hyphen
        ]
        for code in invalid_codes:
            assert validate_short_code(code) is False

    def test_normalize_url(self):
        """Test URL normalization."""
        # Add https if missing
        assert normalize_url("example.com") == "https://example.com"
        assert normalize_url("http://example.com") == "http://example.com"
        assert normalize_url("https://example.com") == "https://example.com"
        # Trim whitespace
        assert normalize_url("  https://example.com  ") == "https://example.com"


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}


class TestCreateShortURL:
    """Tests for POST /shorten endpoint."""

    def test_create_short_url_success(self, client):
        """Test creating a short URL successfully."""
        response = client.post(
            "/shorten",
            json={"original_url": "https://example.com"}
        )
        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        # Note: HttpUrl in Pydantic adds trailing slash
        assert data["original_url"].rstrip("/") == "https://example.com"
        assert len(data["short_code"]) == 6

    def test_create_short_url_with_custom_code(self, client):
        """Test creating a short URL with custom code."""
        response = client.post(
            "/shorten",
            json={
                "original_url": "https://example.com",
                "custom_code": "custom"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["short_code"] == "custom"
        assert "custom" in data["short_url"]

    def test_create_short_url_custom_code_too_short(self, client):
        """Test creating with too short custom code."""
        response = client.post(
            "/shorten",
            json={
                "original_url": "https://example.com",
                "custom_code": "ab"
            }
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_create_short_url_custom_code_too_long(self, client):
        """Test creating with too long custom code."""
        response = client.post(
            "/shorten",
            json={
                "original_url": "https://example.com",
                "custom_code": "a" * 25
            }
        )
        assert response.status_code == 422  # Pydantic validation error

    def test_create_short_url_custom_code_invalid_chars(self, client):
        """Test creating with invalid custom code characters."""
        response = client.post(
            "/shorten",
            json={
                "original_url": "https://example.com",
                "custom_code": "invalid@code"
            }
        )
        assert response.status_code == 400

    def test_create_short_url_duplicate_custom_code(self, client):
        """Test creating with duplicate custom code."""
        # Create first URL with custom code
        response = client.post(
            "/shorten",
            json={
                "original_url": "https://example.com",
                "custom_code": "duplicate"
            }
        )
        assert response.status_code == 201

        # Try to create another with same code
        response = client.post(
            "/shorten",
            json={
                "original_url": "https://example2.com",
                "custom_code": "duplicate"
            }
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_short_url_invalid_url(self, client):
        """Test creating with invalid URL format."""
        response = client.post(
            "/shorten",
            json={"original_url": "not-a-valid-url"}
        )
        assert response.status_code == 422  # Validation error


class TestRedirectEndpoint:
    """Tests for GET /{short_code} endpoint."""

    def test_redirect_success(self, client):
        """Test successful redirect."""
        # Create a short URL first
        create_response = client.post(
            "/shorten",
            json={"original_url": "https://example.com"}
        )
        short_code = create_response.json()["short_code"]

        # Redirect
        response = client.get(f"/{short_code}", follow_redirects=False)
        assert response.status_code == 302
        # Note: HttpUrl in Pydantic adds trailing slash
        assert response.headers["location"].rstrip("/") == "https://example.com"

    def test_redirect_not_found(self, client):
        """Test redirect for non-existent short code."""
        response = client.get("/nonexistent", follow_redirects=False)
        assert response.status_code == 404

    def test_redirect_invalid_code(self, client):
        """Test redirect with invalid short code format."""
        response = client.get("/ab", follow_redirects=False)  # Too short
        assert response.status_code == 404

    def test_redirect_click_count_increments(self, client):
        """Test that redirect increments click count."""
        # Create a short URL
        create_response = client.post(
            "/shorten",
            json={"original_url": "https://example.com"}
        )
        short_code = create_response.json()["short_code"]

        # Get info before redirect
        info_response = client.get(f"/{short_code}/info")
        clicks_before = info_response.json()["clicks"]

        # Redirect multiple times
        for _ in range(3):
            client.get(f"/{short_code}", follow_redirects=False)

        # Get info after redirect
        info_response = client.get(f"/{short_code}/info")
        clicks_after = info_response.json()["clicks"]

        assert clicks_after == clicks_before + 3


class TestDeleteEndpoint:
    """Tests for DELETE /{short_code} endpoint."""

    def test_delete_success(self, client):
        """Test deleting a short URL successfully."""
        # Create a short URL first
        create_response = client.post(
            "/shorten",
            json={"original_url": "https://example.com"}
        )
        short_code = create_response.json()["short_code"]

        # Delete it
        response = client.delete(f"/{short_code}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "URL deleted successfully"
        assert data["short_code"] == short_code

        # Verify it's deleted (can't redirect)
        response = client.get(f"/{short_code}", follow_redirects=False)
        assert response.status_code == 404

    def test_delete_not_found(self, client):
        """Test deleting non-existent short URL."""
        response = client.delete("/nonexistent")
        assert response.status_code == 404

    def test_delete_invalid_code(self, client):
        """Test deleting with invalid short code format."""
        response = client.delete("/ab")  # Too short
        assert response.status_code == 404


class TestUpdateEndpoint:
    """Tests for PUT /{short_code} endpoint."""

    def test_update_success(self, client):
        """Test updating a short URL successfully."""
        # Create a short URL first
        create_response = client.post(
            "/shorten",
            json={"original_url": "https://example.com"}
        )
        short_code = create_response.json()["short_code"]

        # Update it
        response = client.put(
            f"/{short_code}",
            json={"original_url": "https://updated.com"}
        )
        assert response.status_code == 200
        data = response.json()
        # Note: HttpUrl in Pydantic adds trailing slash
        assert data["original_url"].rstrip("/") == "https://updated.com"

        # Verify redirect goes to updated URL
        redirect_response = client.get(
            f"/{short_code}", follow_redirects=False
        )
        assert redirect_response.headers["location"].rstrip("/") == "https://updated.com"

    def test_update_not_found(self, client):
        """Test updating non-existent short URL."""
        response = client.put(
            "/nonexistent",
            json={"original_url": "https://updated.com"}
        )
        assert response.status_code == 404

    def test_update_invalid_code(self, client):
        """Test updating with invalid short code format."""
        response = client.put(
            "/ab",
            json={"original_url": "https://updated.com"}
        )
        assert response.status_code == 404


class TestURLInfoEndpoint:
    """Tests for GET /{short_code}/info endpoint."""

    def test_get_url_info_success(self, client):
        """Test getting URL info successfully."""
        # Create a short URL first
        create_response = client.post(
            "/shorten",
            json={
                "original_url": "https://example.com",
                "custom_code": "infotest"
            }
        )

        # Get info
        response = client.get("/infotest/info")
        assert response.status_code == 200
        data = response.json()
        # Note: HttpUrl in Pydantic adds trailing slash
        assert data["original_url"].rstrip("/") == "https://example.com"
        assert data["short_code"] == "infotest"
        assert "short_url" in data
        assert "created_at" in data
        assert "clicks" in data

    def test_get_url_info_not_found(self, client):
        """Test getting info for non-existent URL."""
        response = client.get("/nonexistent/info")
        assert response.status_code == 404


class TestListURLsEndpoint:
    """Tests for GET / endpoint."""

    def test_list_urls_with_data(self, test_db):
        """Test listing URLs with existing data."""
        from src.core.database import get_db
        # Create URLs
        test_db.create_url("https://example1.com", "list1")
        test_db.create_url("https://example2.com", "list2")
        test_db.create_url("https://example3.com", "list3")

        app.dependency_overrides[get_db] = lambda: test_db
        
        # Store original lifespan
        from contextlib import asynccontextmanager
        original_lifespan = app.router.lifespan_context
        
        @asynccontextmanager
        async def test_lifespan(app):
            yield
        
        app.router.lifespan_context = test_lifespan
        
        with TestClient(app) as list_client:
            response = list_client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
        
        app.router.lifespan_context = original_lifespan
        app.dependency_overrides.clear()


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_url_creation_and_retrieval(self, test_db):
        """Test URL creation and retrieval from database."""
        url = test_db.create_url("https://example.com", "testcode")
        assert url["original_url"] == "https://example.com"
        assert url["short_code"] == "testcode"

        # Retrieve
        retrieved = test_db.get_url_by_code("testcode")
        assert retrieved is not None
        assert retrieved["original_url"] == "https://example.com"

    def test_url_exists(self, test_db):
        """Test checking if URL exists."""
        assert test_db.url_exists("nonexistent") is False

        test_db.create_url("https://example.com", "testcode")
        assert test_db.url_exists("testcode") is True

    def test_url_update(self, test_db):
        """Test updating a URL."""
        test_db.create_url("https://old.com", "updatecode")

        updated = test_db.update_url("updatecode", "https://new.com")
        assert updated["original_url"] == "https://new.com"

    def test_url_delete(self, test_db):
        """Test deleting a URL (soft delete)."""
        test_db.create_url("https://example.com", "deletecode")

        # Should exist before delete
        assert test_db.get_url_by_code("deletecode") is not None

        # Delete
        deleted = test_db.delete_url("deletecode")
        assert deleted is True

        # Should not be found (soft delete)
        assert test_db.get_url_by_code("deletecode") is None

    def test_increment_clicks(self, test_db):
        """Test incrementing click count."""
        test_db.create_url("https://example.com", "clickscode")

        # Get initial clicks
        url = test_db.get_url_by_code("clickscode")
        initial_clicks = url["clicks"]

        # Increment
        test_db.increment_clicks("clickscode")

        # Verify
        url = test_db.get_url_by_code("clickscode")
        assert url["clicks"] == initial_clicks + 1

    def test_get_all_urls(self, test_db):
        """Test getting all URLs."""
        test_db.create_url("https://example1.com", "code1")
        test_db.create_url("https://example2.com", "code2")
        test_db.create_url("https://example3.com", "code3")

        urls = test_db.get_all_urls()
        assert len(urls) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

