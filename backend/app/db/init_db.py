"""Database initialization and schema creation."""

import json
from pathlib import Path
from typing import Dict, Set, Any, Optional
import duckdb


def infer_type(value: Any) -> str:
    """Infer DuckDB type from Python value."""
    if value is None:
        return "VARCHAR"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE"
    return "VARCHAR"


def get_schema_from_jsonl(jsonl_path: Path, sample_size: int = 100) -> Dict[str, str]:
    """Infer schema from JSONL file by sampling records."""
    schema = {}
    
    if not jsonl_path.exists():
        return schema
    
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= sample_size:
                break
            try:
                record = json.loads(line.strip())
                for key, value in record.items():
                    if key not in schema:
                        schema[key] = infer_type(value)
                    # Upgrade type if needed
                    if value is not None:
                        detected = infer_type(value)
                        if detected == "DOUBLE" and schema[key] == "BIGINT":
                            schema[key] = "DOUBLE"
                        elif detected == "VARCHAR" and schema[key] != "VARCHAR":
                            schema[key] = "VARCHAR"
            except (json.JSONDecodeError, ValueError):
                continue
    
    return schema


def create_table_from_jsonl(conn: duckdb.DuckDBPyConnection, table_name: str, jsonl_path: Path) -> Dict[str, str]:
    """Create table from JSONL schema and add normalized columns."""
    schema = get_schema_from_jsonl(jsonl_path)
    
    if not schema:
        raise ValueError(f"Cannot infer schema from {jsonl_path}")
    
    # Add normalized helper columns for composite keys
    schema['_normalized_item_key'] = 'VARCHAR'  # Will hold composite ID
    
    # Build column definitions
    columns = []
    for col_name, col_type in sorted(schema.items()):
        # Sanitize column name
        safe_name = col_name.replace(' ', '_').replace('-', '_').lower()
        columns.append(f"{safe_name} {col_type}")
    
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
    
    try:
        conn.execute(create_sql)
    except Exception as e:
        raise RuntimeError(f"Failed to create table {table_name}: {e}")
    
    return schema


def initialize_database(raw_data_dir: Path) -> duckdb.DuckDBPyConnection:
    """Initialize database by creating tables from JSONL files."""
    db_path = Path(__file__).parent.parent.parent / "data" / "processed" / "o2c_graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not raw_data_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_data_dir}")
    
    conn = duckdb.connect(str(db_path))
    
    # List of collections to load
    collections = [
        "sales_order_headers",
        "sales_order_items",
        "outbound_delivery_headers",
        "outbound_delivery_items",
        "billing_document_headers",
        "billing_document_items",
        "business_partners",
        "products",
        "plants",
    ]
    
    tables_created = []
    
    for collection in collections:
        jsonl_path = raw_data_dir / f"{collection}.jsonl"
        
        if not jsonl_path.exists():
            print(f"⚠️  Missing: {collection}.jsonl")
            continue
        
        try:
            schema = create_table_from_jsonl(conn, collection, jsonl_path)
            tables_created.append(collection)
            print(f"✓ Created table: {collection} with {len(schema)} columns")
        except Exception as e:
            print(f"✗ Failed to create {collection}: {e}")
    
    conn.commit()
    return conn, tables_created