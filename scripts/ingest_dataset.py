#!/usr/bin/env python3
"""Script to ingest the SAP O2C dataset into DuckDB."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db.init_db import initialize_database
from app.services.ingest_service import IngestService
from app.config import Config


def main():
    """Main ingestion function."""
    print("=" * 70)
    print("SAP O2C DATASET INGESTION")
    print("=" * 70)
    
    # Verify raw data exists
    raw_data_dir = Config.RAW_DATA_DIR
    if not raw_data_dir.exists():
        print(f"\n❌ ERROR: Raw data directory not found!")
        print(f"   Expected: {raw_data_dir}")
        print(f"   Please ensure data/raw/sap-o2c-data/sap-o2c-data/ contains JSONL files.")
        sys.exit(1)
    
    print(f"\n✓ Raw data directory found: {raw_data_dir}")
    print(f"✓ Database will be created at: {Config.DATABASE_PATH}")
    
    try:
        # Initialize database and create tables
        print("\n📊 Initializing database schema...")
        conn, tables_created = initialize_database(raw_data_dir)
        print(f"✓ Created {len(tables_created)} tables")
        
        # Ingest data
        print("\n📥 Starting data ingestion...")
        ingest_service = IngestService(conn)
        
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
        
        for collection in collections:
            jsonl_path = raw_data_dir / f"{collection}.jsonl"
            ingest_service.ingest_collection(collection, jsonl_path)
        
        # Print summary
        ingest_service.print_summary()
        
        conn.close()
        print("\n✅ Ingestion complete!")
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()