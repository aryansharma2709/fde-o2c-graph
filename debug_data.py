#!/usr/bin/env python3
"""Debug database initialization."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config import Config

collection_name = "sales_order_headers"
data_dir = Config.RAW_DATA_DIR / collection_name
print(f"Looking for data in: {data_dir}")
print(f"Directory exists: {data_dir.exists()}")

if data_dir.exists():
    files = list(data_dir.glob("*.jsonl"))
    print(f"Found {len(files)} JSONL files")
    if files:
        print(f"First file: {files[0]}")
        # Try to read first record
        with open(files[0], 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            print(f"First line: {first_line[:100]}...")
else:
    print("Directory does not exist")