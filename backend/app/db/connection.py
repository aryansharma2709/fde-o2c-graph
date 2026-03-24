from pathlib import Path

import duckdb


def get_db_path() -> Path:
    """Return the shared DuckDB file path for the whole app."""
    repo_root = Path(__file__).resolve().parents[3]
    db_dir = repo_root / "data" / "processed"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "o2c_graph.db"


def get_db_connection() -> duckdb.DuckDBPyConnection:
    """Return a connection to the shared DuckDB database file."""
    return duckdb.connect(str(get_db_path()))