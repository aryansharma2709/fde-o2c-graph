#!/usr/bin/env python3
"""
Dataset inspection script for SAP Order-to-Cash data.

Extracts metadata from JSONL files in data/raw/sap-o2c-data/sap-o2c-data/
- Lists all collections (tables)
- Counts rows per collection
- Samples schema from first row
- Detects likely key columns
- Outputs a structured audit summary

Usage:
    python scripts/inspect_dataset.py

Output:
    Printed audit report to stdout (suitable for copy/paste into docs)
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Set


def get_dataset_path():
    """Find the dataset directory, either extracted or in zip."""
    base_path = Path(__file__).parent.parent / "data" / "raw"
    
    extracted = base_path / "sap-o2c-data" / "sap-o2c-data"
    if extracted.exists():
        return extracted
    
    zip_path = base_path / "sap-order-to-cash-dataset.zip"
    if zip_path.exists():
        raise FileNotFoundError(
            f"Zip file found at {zip_path} but not extracted. "
            f"Extract it to {base_path}/sap-o2c-data/ first."
        )
    
    raise FileNotFoundError(
        f"Dataset not found at {extracted} or {zip_path}. "
        f"Check data/raw/"
    )


def load_jsonl_files(directory: Path) -> List[Dict[str, Any]]:
    """Load all JSONL files from a directory."""
    records = []
    for file in sorted(directory.glob("*.jsonl")):
        with open(file, "r") as f:
            for line in f:
                records.append(json.loads(line))
    return records


def analyze_collection(name: str, directory: Path) -> Dict[str, Any]:
    """Analyze a collection: row count, schema, key columns."""
    records = load_jsonl_files(directory)
    
    if not records:
        return {
            "name": name,
            "row_count": 0,
            "columns": [],
            "sample": None,
        }
    
    # Collect all unique columns
    all_columns = set()
    for record in records:
        all_columns.update(record.keys())
    
    # Detect likely key columns
    key_candidates = []
    for col in sorted(all_columns):
        # Check if likely a key (common naming patterns)
        if any(x in col.lower() for x in ["id", "key", "number", "document", "order"]):
            # Check if mostly unique
            unique_count = len(set(str(r.get(col)) for r in records if col in r))
            if unique_count > len(records) * 0.8:  # >80% unique
                key_candidates.append(col)
    
    return {
        "name": name,
        "row_count": len(records),
        "columns": sorted(all_columns),
        "key_candidates": key_candidates,
        "sample": records[0] if records else None,
    }


def detect_join_patterns(collections: Dict[str, Dict]) -> List[str]:
    """Look for potential join patterns in column names across collections."""
    patterns = []
    all_columns_by_col_name = defaultdict(list)
    
    for coll_name, info in collections.items():
        for col in info["columns"]:
            all_columns_by_col_name[col].append(coll_name)
    
    # Find columns that appear in multiple collections (likely FKs)
    for col_name, appearances in all_columns_by_col_name.items():
        if len(appearances) > 1:
            patterns.append(f"Column '{col_name}' appears in: {', '.join(appearances)}")
    
    return sorted(patterns)


def main():
    """Audit the dataset and print a summary."""
    dataset_path = get_dataset_path()
    
    print("=" * 80)
    print("SAP ORDER-TO-CASH DATASET AUDIT")
    print(f"Source: {dataset_path}")
    print("=" * 80)
    print()
    
    # Scan all collections
    collections = {}
    for collection_dir in sorted(dataset_path.iterdir()):
        if collection_dir.is_dir():
            name = collection_dir.name
            print(f"Analyzing {name}...", end=" ", flush=True)
            analysis = analyze_collection(name, collection_dir)
            collections[name] = analysis
            print(f"✓ {analysis['row_count']} rows, {len(analysis['columns'])} columns")
    
    print()
    print("=" * 80)
    print("COLLECTION INVENTORY")
    print("=" * 80)
    print()
    
    total_rows = 0
    for name in sorted(collections.keys()):
        info = collections[name]
        total_rows += info["row_count"]
        print(f"{name}")
        print(f"  Rows: {info['row_count']}")
        print(f"  Columns: {', '.join(sorted(info['columns']))}")
        if info["key_candidates"]:
            print(f"  Likely Keys: {', '.join(info['key_candidates'])}")
        print()
    
    print(f"TOTAL ROWS: {total_rows}")
    print()
    
    # Print potential join patterns
    print("=" * 80)
    print("CROSS-COLLECTION COLUMN REFERENCES (Potential Joins)")
    print("=" * 80)
    print()
    
    patterns = detect_join_patterns(collections)
    for pattern in patterns:
        print(f"  {pattern}")
    print()
    
    # Print sample data for key collections
    key_collections = [
        "sales_order_headers",
        "sales_order_items",
        "outbound_delivery_headers",
        "outbound_delivery_items",
        "billing_document_headers",
        "billing_document_items",
        "payments_accounts_receivable",
        "business_partners",
        "products",
    ]
    
    print("=" * 80)
    print("SAMPLE DATA FROM KEY COLLECTIONS")
    print("=" * 80)
    print()
    
    for coll_name in key_collections:
        if coll_name in collections:
            info = collections[coll_name]
            if info["sample"]:
                print(f"{coll_name}")
                print(f"  Sample row: {json.dumps(info['sample'], indent=4)}")
                print()
    
    # Detailed column listings
    print("=" * 80)
    print("DETAILED COLUMN LISTINGS")
    print("=" * 80)
    print()
    
    for coll_name in sorted(collections.keys()):
        info = collections[coll_name]
        print(f"{coll_name}:")
        for col in sorted(info['columns']):
            print(f"  - {col}")
        print()


if __name__ == "__main__":
    main()
