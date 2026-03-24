from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import duckdb

from .connection import get_db_connection


CORE_COLLECTIONS = [
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


def _sanitize_column_name(key: str) -> str:
    return key.replace(" ", "_").replace("-", "_").lower()


def _infer_duckdb_type(value: Any) -> str:
    if value is None:
        return "VARCHAR"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE"
    return "VARCHAR"


def _load_sample_record(jsonl_path: Path) -> Dict[str, Any]:
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                return json.loads(line)
    return {}


def _resolve_part_files(collection_dir: Path) -> List[Path]:
    if not collection_dir.exists() or not collection_dir.is_dir():
        return []
    part_files = sorted(collection_dir.glob("part-*.jsonl"))
    if part_files:
        return part_files
    return sorted(collection_dir.glob("*.jsonl"))


def _create_table_from_sample(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    sample_record: Dict[str, Any],
) -> None:
    columns: List[str] = []

    for raw_key, raw_value in sample_record.items():
        col = _sanitize_column_name(raw_key)
        col_type = _infer_duckdb_type(raw_value)
        columns.append(f'"{col}" {col_type}')

    # Minimal normalized helper column for item tables
    if table_name in {"sales_order_items", "outbound_delivery_items", "billing_document_items"}:
        columns.append('"_normalized_item_key" VARCHAR')

    ddl = f'DROP TABLE IF EXISTS "{table_name}";'
    conn.execute(ddl)

    create_sql = f'''
        CREATE TABLE "{table_name}" (
            {", ".join(columns)}
        )
    '''
    conn.execute(create_sql)


def create_graph_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("DROP TABLE IF EXISTS graph_edges")
    conn.execute("DROP TABLE IF EXISTS graph_nodes")

    conn.execute(
        """
        CREATE TABLE graph_nodes (
            node_id VARCHAR PRIMARY KEY,
            node_type VARCHAR NOT NULL,
            label VARCHAR NOT NULL,
            metadata_json JSON
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE graph_edges (
            edge_id VARCHAR PRIMARY KEY,
            source_id VARCHAR NOT NULL,
            target_id VARCHAR NOT NULL,
            edge_type VARCHAR NOT NULL,
            metadata_json JSON
        )
        """
    )

    conn.commit()


def initialize_database(dataset_root: Path) -> Tuple[duckdb.DuckDBPyConnection, List[str]]:
    """
    Initialize the single shared DuckDB database and recreate all core tables
    from dataset samples.
    """
    conn = get_db_connection()
    tables_created: List[str] = []

    print(f"✓ Dataset root: {dataset_root}")

    for collection in CORE_COLLECTIONS:
        collection_dir = dataset_root / collection
        part_files = _resolve_part_files(collection_dir)

        if not part_files:
            print(f"⚠️  Missing collection: {collection}")
            continue

        sample_record = _load_sample_record(part_files[0])
        if not sample_record:
            print(f"⚠️  Empty collection: {collection}")
            continue

        _create_table_from_sample(conn, collection, sample_record)
        tables_created.append(collection)
        print(f"✓ Created table: {collection} with {len(sample_record) + (1 if collection in {'sales_order_items', 'outbound_delivery_items', 'billing_document_items'} else 0)} columns ({len(part_files)} part files)")

    create_graph_tables(conn)
    print("✓ Created graph projection tables: graph_nodes, graph_edges")

    conn.commit()
    return conn, tables_created