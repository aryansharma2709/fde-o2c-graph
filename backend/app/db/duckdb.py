"""DuckDB database connection and utilities."""

import duckdb
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from ..config import Config


class DuckDBConnection:
    """DuckDB connection manager."""

    def __init__(self, db_path: Path = Config.DATABASE_PATH):
        self.db_path = db_path
        self._conn = None

    @contextmanager
    def get_connection(self):
        """Get a DuckDB connection."""
        conn = duckdb.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def execute_query(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a query and return results as dicts."""
        with self.get_connection() as conn:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            return [dict(row) for row in result.fetchall()]

    def execute_ddl(self, query: str) -> None:
        """Execute DDL statements."""
        with self.get_connection() as conn:
            conn.execute(query)

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists."""
        result = self.execute_query(
            "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name = ?",
            [table_name]
        )
        return result[0]['count'] > 0

    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table."""
        result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        return result[0]['count'] if result else 0

    def get_table_names(self) -> List[str]:
        """Get all table names."""
        result = self.execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        )
        return [row['table_name'] for row in result]


# Global instance
db = DuckDBConnection()