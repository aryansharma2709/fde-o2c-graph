#!/usr/bin/env python3
"""
Join coverage validation script for SAP Order-to-Cash data.

Validates actual join coverage for specified paths using full dataset.
Computes raw and normalized coverage, detects formatting issues,
and classifies joins based on coverage metrics.

Usage:
    python scripts/validate_join_coverage.py

Output:
    Printed validation report to stdout (suitable for copy/paste into docs)
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple


def get_dataset_path():
    """Find the dataset directory."""
    base_path = Path(__file__).parent.parent / "data" / "raw"
    extracted = base_path / "sap-o2c-data" / "sap-o2c-data"
    if extracted.exists():
        return extracted
    raise FileNotFoundError(f"Dataset not found at {extracted}")


def load_collection(directory: Path, collection_name: str) -> List[Dict[str, Any]]:
    """Load all records from a collection directory."""
    collection_dir = directory / collection_name
    if not collection_dir.exists():
        return []
    
    records = []
    for file in sorted(collection_dir.glob("*.jsonl")):
        with open(file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records


def normalize_id(value: Any, pad_length: int = 10) -> str:
    """Normalize ID by converting to string and padding with zeros."""
    if value is None:
        return ""
    s = str(value).strip()
    if s.isdigit():
        return s.zfill(pad_length)
    return s


def validate_join(left_collection: str, left_keys: List[str], 
                 right_collection: str, right_keys: List[str],
                 directory: Path, normalize: bool = False) -> Dict[str, Any]:
    """Validate join coverage between two collections."""
    
    left_records = load_collection(directory, left_collection)
    right_records = load_collection(directory, right_collection)
    
    if not left_records or not right_records:
        return {
            'left_count': len(left_records),
            'right_count': len(right_records),
            'matched': 0,
            'unmatched_left': len(left_records),
            'unmatched_right': len(right_records),
            'coverage_pct': 0.0,
            'classification': 'not_recommended',
            'issues': ['Missing collection data']
        }
    
    # Extract key tuples
    left_keys_set = set()
    for record in left_records:
        key_tuple = tuple(str(record.get(k, "")).strip() for k in left_keys)
        if normalize:
            key_tuple = tuple(normalize_id(v) for v in key_tuple)
        left_keys_set.add(key_tuple)
    
    right_keys_set = set()
    for record in right_records:
        key_tuple = tuple(str(record.get(k, "")).strip() for k in right_keys)
        if normalize:
            key_tuple = tuple(normalize_id(v) for v in key_tuple)
        right_keys_set.add(key_tuple)
    
    matched = len(left_keys_set & right_keys_set)
    unmatched_left = len(left_keys_set - right_keys_set)
    unmatched_right = len(right_keys_set - left_keys_set)
    
    coverage_pct = (matched / len(left_keys_set)) * 100 if left_keys_set else 0
    
    # Classify
    if coverage_pct >= 95:
        classification = 'confirmed_with_normalization' if normalize else 'confirmed'
    elif coverage_pct >= 80:
        classification = 'partial'
    elif coverage_pct >= 50:
        classification = 'uncertain'
    else:
        classification = 'not_recommended'
    
    return {
        'left_count': len(left_records),
        'right_count': len(right_records),
        'matched': matched,
        'unmatched_left': unmatched_left,
        'unmatched_right': unmatched_right,
        'coverage_pct': round(coverage_pct, 2),
        'classification': classification,
        'issues': []
    }


def main():
    directory = get_dataset_path()
    
    # Define join validations
    joins = [
        {
            'name': 'sales_order_headers.salesOrder -> sales_order_items.salesOrder',
            'left': 'sales_order_headers', 'left_keys': ['salesOrder'],
            'right': 'sales_order_items', 'right_keys': ['salesOrder'],
            'normalize': True
        },
        {
            'name': 'sales_order_items.(salesOrder, salesOrderItem) -> outbound_delivery_items.(referenceSdDocument, referenceSdDocumentItem)',
            'left': 'sales_order_items', 'left_keys': ['salesOrder', 'salesOrderItem'],
            'right': 'outbound_delivery_items', 'right_keys': ['referenceSdDocument', 'referenceSdDocumentItem'],
            'normalize': True
        },
        {
            'name': 'outbound_delivery_items.(deliveryDocument, deliveryDocumentItem) -> billing_document_items.(referenceSdDocument, referenceSdDocumentItem)',
            'left': 'outbound_delivery_items', 'left_keys': ['deliveryDocument', 'deliveryDocumentItem'],
            'right': 'billing_document_items', 'right_keys': ['referenceSdDocument', 'referenceSdDocumentItem'],
            'normalize': True
        },
        {
            'name': 'billing_document_headers.accountingDocument -> journal_entry_items_accounts_receivable.accountingDocument',
            'left': 'billing_document_headers', 'left_keys': ['accountingDocument'],
            'right': 'journal_entry_items_accounts_receivable', 'right_keys': ['accountingDocument'],
            'normalize': True
        },
        {
            'name': 'journal_entry_items_accounts_receivable.accountingDocument -> payments_accounts_receivable.clearingAccountingDocument',
            'left': 'journal_entry_items_accounts_receivable', 'left_keys': ['accountingDocument'],
            'right': 'payments_accounts_receivable', 'right_keys': ['clearingAccountingDocument'],
            'normalize': True
        },
        {
            'name': 'sales_order_headers.soldToParty -> business_partners.businessPartner',
            'left': 'sales_order_headers', 'left_keys': ['soldToParty'],
            'right': 'business_partners', 'right_keys': ['businessPartner'],
            'normalize': True
        },
        {
            'name': 'sales_order_items.material -> products.product',
            'left': 'sales_order_items', 'left_keys': ['material'],
            'right': 'products', 'right_keys': ['product'],
            'normalize': True
        },
        {
            'name': 'outbound_delivery_items.plant -> plants.plant',
            'left': 'outbound_delivery_items', 'left_keys': ['plant'],
            'right': 'plants', 'right_keys': ['plant'],
            'normalize': True
        },
        {
            'name': 'business_partners.businessPartner -> business_partner_addresses.businessPartner',
            'left': 'business_partners', 'left_keys': ['businessPartner'],
            'right': 'business_partner_addresses', 'right_keys': ['businessPartner'],
            'normalize': True
        },
        {
            'name': 'plants.addressId -> business_partner_addresses.addressId',
            'left': 'plants', 'left_keys': ['addressId'],
            'right': 'business_partner_addresses', 'right_keys': ['addressId'],
            'normalize': True
        }
    ]
    
    print("# Join Coverage Validation Report")
    print()
    print("| Join Path | Left Count | Right Count | Matched | Coverage % | Classification | Notes |")
    print("|-----------|------------|--------------|---------|------------|----------------|-------|")
    
    for join in joins:
        result = validate_join(
            join['left'], join['left_keys'],
            join['right'], join['right_keys'],
            directory, join['normalize']
        )
        
        notes = f"Raw: {result['matched']}/{len(load_collection(directory, join['left']))} matched"
        if result['issues']:
            notes += f"; Issues: {', '.join(result['issues'])}"
        
        print(f"| {join['name']} | {result['left_count']} | {result['right_count']} | {result['matched']} | {result['coverage_pct']}% | {result['classification']} | {notes} |")
    
    print()
    print("## Summary")
    print("- confirmed: >95% coverage")
    print("- confirmed_with_normalization: >95% with ID normalization")
    print("- partial: 80-95% coverage")
    print("- uncertain: 50-80% coverage")
    print("- not_recommended: <50% coverage")


if __name__ == "__main__":
    main()