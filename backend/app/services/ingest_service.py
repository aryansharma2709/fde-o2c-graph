"""Data ingestion service for loading SAP O2C data into DuckDB."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import duckdb


class IngestService:
    """Service for ingesting partitioned JSONL SAP O2C data into DuckDB."""

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        self.conn = conn
        self.stats: Dict[str, Dict[str, int]] = {}

    @staticmethod
    def find_repo_root(start: Path) -> Path:
        """Walk upward until we find the repository root."""
        current = start.resolve()
        for path in [current, *current.parents]:
            if (path / ".git").exists() or (path / "data" / "raw").exists():
                return path
        raise FileNotFoundError("Could not find repository root from current file path.")

    @classmethod
    def find_dataset_root(cls) -> Path:
        """
        Find the correct dataset root.

        Supports both:
        - data/raw/sap-o2c-data
        - data/raw/sap-o2c-data/sap-o2c-data
        """
        repo_root = cls.find_repo_root(Path(__file__))
        base_path = repo_root / "data" / "raw"

        nested_path = base_path / "sap-o2c-data" / "sap-o2c-data"
        direct_path = base_path / "sap-o2c-data"

        if nested_path.exists() and nested_path.is_dir():
            return nested_path
        if direct_path.exists() and direct_path.is_dir():
            return direct_path

        raise FileNotFoundError(
            f"Dataset root not found. Checked: {nested_path}, {direct_path}"
        )

    def validate_dataset_exists(self) -> Path:
        """Validate that the dataset directory exists and return the root."""
        dataset_root = self.find_dataset_root()
        print(f"✓ Dataset root detected: {dataset_root}")
        return dataset_root

    @staticmethod
    def _sanitize_column_name(key: str) -> str:
        """Sanitize incoming JSON keys to SQL-safe column names."""
        return key.replace(" ", "_").replace("-", "_").lower()

    @staticmethod
    def _normalize_item_number(value: Any) -> str:
        """Normalize item identifiers so joins don't fail on '10' vs '000010'."""
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if text.isdigit():
            return text.zfill(6)
        return text

    def normalize_record(self, record: Dict[str, Any], table_name: str) -> Dict[str, Any]:
        """Normalize record data and add helper columns."""
        normalized: Dict[str, Any] = {}

        for key, value in record.items():
            safe_key = self._sanitize_column_name(key)
            normalized[safe_key] = value

        # Keep helper logic minimal so it matches the current table schema.
        # Only add one derived helper column.
        if table_name == "sales_order_items":
            order_id = str(normalized.get("salesorder", "") or "")
            item_id = self._normalize_item_number(normalized.get("salesorderitem", ""))
            normalized["_normalized_item_key"] = f"{order_id}_{item_id}"

        elif table_name == "outbound_delivery_items":
            delivery_id = str(normalized.get("deliverydocument", "") or "")
            item_id = self._normalize_item_number(normalized.get("deliverydocumentitem", ""))
            normalized["_normalized_item_key"] = f"{delivery_id}_{item_id}"

        elif table_name == "billing_document_items":
            billing_id = str(normalized.get("billingdocument", "") or "")
            item_id = self._normalize_item_number(normalized.get("billingdocumentitem", ""))
            normalized["_normalized_item_key"] = f"{billing_id}_{item_id}"

        return normalized

    @staticmethod
    def _resolve_collection_path(table_name: str, source_path: Path) -> Path:
        """
        Resolve a collection path robustly.

        Handles:
        - direct collection folder path
        - single .jsonl file path
        - incorrect <table>.jsonl path by converting it to <table>/ folder
        """
        if source_path.exists():
            return source_path

        if source_path.suffix == ".jsonl":
            candidate_dir = source_path.with_suffix("")
            if candidate_dir.exists() and candidate_dir.is_dir():
                return candidate_dir

        candidate = source_path / table_name
        if candidate.exists() and candidate.is_dir():
            return candidate

        return source_path

    @staticmethod
    def _iter_jsonl_files(collection_path: Path) -> List[Path]:
        """Return all JSONL files for a collection."""
        if collection_path.is_file() and collection_path.suffix == ".jsonl":
            return [collection_path]

        if collection_path.is_dir():
            part_files = sorted(collection_path.glob("part-*.jsonl"))
            if part_files:
                return part_files

            jsonl_files = sorted(collection_path.glob("*.jsonl"))
            if jsonl_files:
                return jsonl_files

        return []

    def insert_records(self, table_name: str, source_path: Path) -> int:
        """Load records from one or more JSONL files into a table."""
        collection_path = self._resolve_collection_path(table_name, source_path)
        jsonl_files = self._iter_jsonl_files(collection_path)

        if not jsonl_files:
            self.stats[table_name] = {"inserted": 0, "errors": 0, "files": 0}
            return 0

        inserted = 0
        errors = 0

        for jsonl_path in jsonl_files:
            with open(jsonl_path, "r", encoding="utf-8") as f:
                for i, line in enumerate(f, start=1):
                    if not line.strip():
                        continue

                    try:
                        record = json.loads(line)
                        normalized = self.normalize_record(record, table_name)

                        columns = list(normalized.keys())
                        placeholders = ",".join(["?" for _ in columns])
                        values = [normalized[col] for col in columns]

                        insert_sql = (
                            f"INSERT INTO {table_name} ({','.join(columns)}) "
                            f"VALUES ({placeholders})"
                        )
                        self.conn.execute(insert_sql, values)
                        inserted += 1

                    except (json.JSONDecodeError, ValueError):
                        errors += 1
                    except Exception:
                        errors += 1

                    if i % 1000 == 0:
                        self.conn.commit()

        self.conn.commit()
        self.stats[table_name] = {
            "inserted": inserted,
            "errors": errors,
            "files": len(jsonl_files),
        }
        return inserted

    def ingest_collection(self, table_name: str, source_path: Path) -> None:
        """Ingest a single collection from a file or folder path."""
        collection_path = self._resolve_collection_path(table_name, source_path)
        jsonl_files = self._iter_jsonl_files(collection_path)

        if not jsonl_files:
            print(f"⚠️  Skipping {table_name}: no JSONL files found")
            self.stats[table_name] = {"inserted": 0, "errors": 0, "files": 0}
            return

        print(
            f"📥 Ingesting {table_name} "
            f"({len(jsonl_files)} file{'s' if len(jsonl_files) != 1 else ''})...",
            end=" ",
            flush=True,
        )
        inserted = self.insert_records(table_name, collection_path)
        print(f"✓ {inserted} rows")

    def print_summary(self) -> None:
        """Print ingestion summary."""
        print("\n" + "=" * 72)
        print("INGESTION SUMMARY")
        print("=" * 72)

        total_inserted = 0
        total_errors = 0
        total_files = 0

        for table_name, stats in sorted(self.stats.items()):
            inserted = stats.get("inserted", 0)
            errors = stats.get("errors", 0)
            files = stats.get("files", 0)

            total_inserted += inserted
            total_errors += errors
            total_files += files

            status = "✓" if errors == 0 else "⚠"
            print(
                f"{status} {table_name:40s} "
                f"{inserted:8d} rows   {files:3d} file(s)",
                end=""
            )
            if errors > 0:
                print(f"   ({errors} errors)")
            else:
                print()

        print("-" * 72)
        print(f"{'TOTAL':40s} {total_inserted:8d} rows   {total_files:3d} file(s)")
        if total_errors > 0:
            print(f"{'Errors':40s} {total_errors:8d}")
        print("=" * 72)