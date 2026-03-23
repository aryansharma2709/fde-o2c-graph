#!/usr/bin/env python3
"""Debug table creation."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config import Config
from app.db.init_db import get_all_fields_from_collection, create_table_from_fields

print("Collections:", Config.COLLECTIONS[:3])

for collection in Config.COLLECTIONS[:1]:  # Test first one
    print(f"\nProcessing {collection}...")
    fields = get_all_fields_from_collection(collection)
    print(f"Found {len(fields)} fields")
    if fields:
        print("Creating table...")
        create_table_from_fields(collection, fields)
        print("Table created successfully")