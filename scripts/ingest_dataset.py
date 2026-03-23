#!/usr/bin/env python3
"""Script to ingest the SAP O2C dataset into DuckDB."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db.init_db import initialize_database
from app.services.ingest_service import IngestService


def main():
    """Main ingestion function."""
    print("=" * 80)
    print("SAP O2C DATASET INGESTION")
    print("=" * 80)
    
    try:
        # Find dataset root
        temp_service = IngestService(None)  # Temporary instance just for validation
        dataset_root = temp_service.validate_dataset_exists()
        
        # Initialize database and create tables
        print("\n📊 Initializing database schema...")
        conn, tables_created = initialize_database(dataset_root)
        print(f"✓ Created {len(tables_created)} tables")
        
        # Ingest data from each collection folder
        print("\n📥 Starting data ingestion...")
        ingest_service = IngestService(conn)
        
        # Required core collections (fail if missing)
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
        ]
        
        # Optional collections (warn if missing)
        optional_collections = [
            "journal_entry_items_accounts_receivable",
            "payments_accounts_receivable",
            "business_partner_addresses",
        ]
        
        missing_required = []
        for collection in required_collections + optional_collections:
            collection_dir = dataset_root / collection
            if collection_dir.exists():
                ingest_service.ingest_collection(collection, collection_dir)
            else:
                if collection in required_collections:
                    missing_required.append(collection)
                else:
                    print(f"⚠️  Optional collection missing: {collection}")
        
        if missing_required:
            print(f"\n❌ ERROR: Missing required collections: {', '.join(missing_required)}")
            conn.close()
            sys.exit(1)
        
        # Print summary
        ingest_service.print_summary()
        
        conn.close()
        print("\n✅ Ingestion complete!")
        print("\n" + "=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()