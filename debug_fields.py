#!/usr/bin/env python3
"""Debug field collection."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db.init_db import get_all_fields_from_collection

collection_name = "sales_order_headers"
fields = get_all_fields_from_collection(collection_name)
print(f"Fields found for {collection_name}: {len(fields)}")
print("Sample fields:", sorted(list(fields))[:10])