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


def get_schema_from_collection(collection_dir: Path, sample_size: int = 100) -> Dict[str, str]:
    """Infer schema from all part files in a collection folder."""
    schema = {}
    
    if not collection_dir.exists() or not collection_dir.is_dir():
        return schema
    
    # Find all part-*.jsonl files
    part_files = list(collection_dir.glob("part-*.jsonl"))
    if not part_files:
        return schema
    
    records_sampled = 0
    
    for part_file in sorted(part_files):
        with open(part_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if records_sampled >= sample_size:
                    break
                    
                if not line.strip():
                    continue
                    
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
                    
                    records_sampled += 1
                    
                except (json.JSONDecodeError, ValueError):
                    continue
        
        if records_sampled >= sample_size:
            break
    
    return schema


def create_table_from_collection(conn: duckdb.DuckDBPyConnection, table_name: str, collection_dir: Path) -> Dict[str, str]:
    """Create table from collection folder schema and add normalized columns."""
    schema = get_schema_from_collection(collection_dir)
    
    if not schema:
        raise ValueError(f"Cannot infer schema from collection {collection_dir}")
    
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


def find_dataset_root() -> Path:
    """Find the correct dataset root directory."""
    base_path = Path(__file__).parent.parent.parent / "data" / "raw"
    
    # Check for nested structure first
    nested_path = base_path / "sap-o2c-data" / "sap-o2c-data"
    if nested_path.exists() and nested_path.is_dir():
        return nested_path
    
    # Check for direct structure
    direct_path = base_path / "sap-o2c-data"
    if direct_path.exists() and direct_path.is_dir():
        return direct_path
    
    raise FileNotFoundError(f"Dataset root not found. Checked: {nested_path}, {direct_path}")


def initialize_database(dataset_root: Path) -> tuple[duckdb.DuckDBPyConnection, list[str]]:
    """Initialize database by creating tables from collection folders."""
    db_path = Path(__file__).parent.parent.parent / "data" / "processed" / "o2c_graph.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"✓ Dataset root: {dataset_root}")
    
    conn = duckdb.connect(str(db_path))
    
    # Required core collections
    required_collections = [
        "sales_order_headers",
        "sales_order_items",
        "outbound_delivery_headers",
        "outbound_delivery_items",
        "billing_document_headers",
        "billing_document_items",
        "business_partners",
        "products",
        "plants",
        "journal_entry_items_accounts_receivable",
        "payments_accounts_receivable",
        "business_partner_addresses",
    ]
    
    tables_created = []
    
    for collection in required_collections:
        collection_dir = dataset_root / collection
        
        if not collection_dir.exists():
            print(f"⚠️  Missing required collection: {collection}")
            continue
        
        try:
            schema = create_table_from_collection(conn, collection, collection_dir)
            tables_created.append(collection)
            part_files = list(collection_dir.glob("part-*.jsonl"))
            print(f"✓ Created table: {collection} with {len(schema)} columns ({len(part_files)} part files)")
        except Exception as e:
            print(f"✗ Failed to create {collection}: {e}")
    
    conn.commit()
    return conn, tables_created