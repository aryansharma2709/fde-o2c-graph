"""Database connection management for DuckDB."""

import duckdb
from pathlib import Path
from ..config import settings


_connection = None


def get_db_connection():
    """Get or create DuckDB connection."""
    global _connection
    if _connection is None:
        db_path = Path(settings.DATABASE_PATH)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _connection = duckdb.connect(str(db_path))
    return _connection


def close_db_connection():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
