"""Database module for URL Shortener Service.

This module handles SQLite database operations and provides
dependency injection for FastAPI endpoints.
"""

import sqlite3
import logging
from typing import Optional

from .config import settings

logger = logging.getLogger(__name__)


class Database:
    """Database class for managing SQLite connections and operations."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Use ":memory:" for in-memory database.
        """
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = settings.database_url
        self._connection: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        """Create or return the database connection.

        For in-memory databases (":memory:"), allows access from multiple threads.
        For file-based databases, creates new connections per operation.

        Returns:
            SQLite connection.
        """
        if self._connection is None:
            # For in-memory databases, allow access from multiple threads
            if self.db_path == ":memory:":
                self._connection = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False
                )
            else:
                self._connection = sqlite3.connect(self.db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
        return self._connection

    def close(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def init_db(self) -> None:
        """Initialize database tables."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL,
            short_code TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            clicks INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
        """
        create_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_short_code ON urls(short_code);
        CREATE INDEX IF NOT EXISTS idx_created_at ON urls(created_at);
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(create_table_sql)
            cursor.executescript(create_index_sql)
            conn.commit()
            logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def execute(
        self, query: str, params: tuple = (), fetch: bool = False
    ) -> Optional[list[sqlite3.Row]]:
        """Execute a SQL query.

        Args:
            query: SQL query string.
            params: Query parameters.
            fetch: Whether to fetch results.

        Returns:
            Query results if fetch=True, None otherwise.
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetch:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            conn.commit()
            return None
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def get_url_by_code(self, short_code: str) -> Optional[dict]:
        """Get URL record by short code.

        Args:
            short_code: The short URL code.

        Returns:
            URL record or None if not found.
        """
        query = "SELECT * FROM urls WHERE short_code = ? AND is_active = 1"
        results = self.execute(query, (short_code,), fetch=True)
        return results[0] if results else None

    def get_url_by_id(self, url_id: int) -> Optional[dict]:
        """Get URL record by ID.

        Args:
            url_id: The URL ID.

        Returns:
            URL record or None if not found.
        """
        query = "SELECT * FROM urls WHERE id = ?"
        results = self.execute(query, (url_id,), fetch=True)
        return results[0] if results else None

    def create_url(
        self, original_url: str, short_code: str, expires_at: Optional[str] = None
    ) -> dict:
        """Create a new shortened URL.

        Args:
            original_url: The original long URL.
            short_code: The short URL code.
            expires_at: Optional expiration timestamp.

        Returns:
            Created URL record.
        """
        query = """
        INSERT INTO urls (original_url, short_code, expires_at)
        VALUES (?, ?, ?)
        """
        self.execute(query, (original_url, short_code, expires_at))
        logger.info(f"Created short URL: {short_code}")
        return self.get_url_by_code(short_code)

    def update_url(
        self, short_code: str, new_original_url: str
    ) -> Optional[dict]:
        """Update original URL for a short code.

        Args:
            short_code: The short URL code.
            new_original_url: The new original URL.

        Returns:
            Updated URL record or None if not found.
        """
        query = "UPDATE urls SET original_url = ? WHERE short_code = ?"
        self.execute(query, (new_original_url, short_code))
        logger.info(f"Updated URL: {short_code}")
        return self.get_url_by_code(short_code)

    def delete_url(self, short_code: str) -> bool:
        """Soft delete a URL (mark as inactive).

        Args:
            short_code: The short URL code.

        Returns:
            True if deleted, False if not found.
        """
        conn = self._get_connection()
        try:
            query = "UPDATE urls SET is_active = 0 WHERE short_code = ?"
            cursor = conn.cursor()
            cursor.execute(query, (short_code,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Deleted short URL: {short_code}")
            return deleted > 0
        except sqlite3.Error as e:
            logger.error(f"Delete failed: {e}")
            raise

    def increment_clicks(self, short_code: str) -> None:
        """Increment click count for a URL.

        Args:
            short_code: The short URL code.
        """
        query = "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?"
        self.execute(query, (short_code,))

    def get_all_urls(self) -> list[dict]:
        """Get all active URLs.

        Returns:
            List of URL records.
        """
        query = "SELECT * FROM urls WHERE is_active = 1 ORDER BY created_at DESC"
        return self.execute(query, fetch=True) or []

    def url_exists(self, short_code: str) -> bool:
        """Check if a short code already exists.

        Args:
            short_code: The short URL code.

        Returns:
            True if exists, False otherwise.
        """
        query = "SELECT 1 FROM urls WHERE short_code = ?"
        results = self.execute(query, (short_code,), fetch=True)
        return len(results) > 0 if results else False


# Global database instance
db = Database()


def get_db() -> Database:
    """Get database instance for dependency injection.

    Returns:
        Database instance.
    """
    return db


def get_test_db() -> Database:
    """Get a fresh in-memory database for testing.

    Returns:
        In-memory Database instance.
    """
    test_db = Database(":memory:")
    test_db.init_db()
    return test_db

