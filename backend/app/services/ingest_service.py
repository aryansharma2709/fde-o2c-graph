"""Data ingestion service for loading SAP O2C data into DuckDB."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import duckdb


class IngestService:
    """Service for ingesting JSONL data into DuckDB."""
    
    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.stats = {}
    
    @staticmethod
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
    
    def validate_dataset_exists(self) -> Path:
        """Validate that the dataset directory exists and return the root."""
        dataset_root = self.find_dataset_root()
        print(f"✓ Dataset root detected: {dataset_root}")
        return dataset_root
    
    def normalize_record(self, record: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Normalize record data (sanitize column names, compute helper fields)."""
        normalized = {}
        
        # Sanitize column names to match table schema
        for key, value in record.items():
            safe_key = key.replace(' ', '_').replace('-', '_').lower()
            normalized[safe_key] = value
        
        # Add normalized composite keys for items
        if table_name == 'sales_order_items':
            order_id = normalized.get('salesorder', '')
            item_id = normalized.get('salesorderitem', '')
            normalized['_normalized_item_key'] = f"{order_id}_{item_id}"
        
        elif table_name == 'outbound_delivery_items':
            delivery_id = normalized.get('deliverydocument', '')
            item_id = normalized.get('deliverydocumentitem', '')
            normalized['_normalized_item_key'] = f"{delivery_id}_{item_id}"
        
        elif table_name == 'billing_document_items':
            doc_id = normalized.get('billingdocument', '')
            item_id = normalized.get('billingdocumentitem', '')
            normalized['_normalized_item_key'] = f"{doc_id}_{item_id}"
        
        return normalized
    
    def insert_records(self, table_name: str, jsonl_path: Path) -> int:
        """Load records from JSONL into table."""
        if not jsonl_path.exists():
            return 0
        
        inserted = 0
        errors = 0
        
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                
                try:
                    record = json.loads(line)
                    normalized = self.normalize_record(record, table_name)
                    
                    # Build INSERT statement dynamically
                    columns = list(normalized.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    values = [normalized[col] for col in columns]
                    
                    insert_sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
                    
                    self.conn.execute(insert_sql, values)
                    inserted += 1
                    
                except (json.JSONDecodeError, ValueError):
                    errors += 1
                except Exception:
                    errors += 1
                
                # Commit every 1000 records for performance
                if (i + 1) % 1000 == 0:
                    self.conn.commit()
        
        self.conn.commit()
        self.stats[table_name] = {"inserted": inserted, "errors": errors}
        
        return inserted
    
    def ingest_collection(self, table_name: str, jsonl_path: Path) -> None:
        """Ingest a single collection."""
        if not jsonl_path.exists():
            print(f"⚠️  Skipping {table_name}: file not found")
            return
        
        print(f"📥 Ingesting {table_name}...", end=" ", flush=True)
        inserted = self.insert_records(table_name, jsonl_path)
        print(f"✓ {inserted} rows")
    
    def print_summary(self) -> None:
        """Print ingestion summary."""
        print("\n" + "="*60)
        print("INGESTION SUMMARY")
        print("="*60)
        
        total_inserted = 0
        total_errors = 0
        
        for table_name, stats in sorted(self.stats.items()):
            inserted = stats.get("inserted", 0)
            errors = stats.get("errors", 0)
            total_inserted += inserted
            total_errors += errors
            
            status = "✓" if errors == 0 else "⚠"
            print(f"{status} {table_name:40s} {inserted:8d} rows", end="")
            if errors > 0:
                print(f" ({errors} errors)")
            else:
                print()
        
        print("-"*60)
        print(f"{'TOTAL':40s} {total_inserted:8d} rows")
        if total_errors > 0:
            print(f"{'Errors':40s} {total_errors:8d}")
        print("="*60)
