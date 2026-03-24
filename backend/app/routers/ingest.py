from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..db.init_db import initialize_database
from ..services.graph_service import GraphService
from ..services.ingest_service import IngestService

router = APIRouter()


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


def _table_count(conn, table_name: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
    return int(row[0]) if row else 0


@router.post("/ingest")
def ingest_dataset() -> Dict[str, Any]:
    """Ingest the SAP O2C dataset and build graph projections."""
    conn = None
    try:
        dataset_root = IngestService.find_dataset_root()

        # Create schema + graph tables on one shared connection
        conn, _ = initialize_database(dataset_root)

        # Ingest relational tables
        ingest_service = IngestService(conn)
        relational_counts: Dict[str, int] = {}

        # Clear all relational tables before ingesting to ensure idempotency
        for collection in CORE_COLLECTIONS:
            conn.execute(f"DELETE FROM {collection}")

        for collection in CORE_COLLECTIONS:
            collection_path = dataset_root / collection
            ingest_service.ingest_collection(collection, collection_path)
            relational_counts[collection] = _table_count(conn, collection)

        # Build graph on the same shared connection
        graph_service = GraphService(conn)
        graph_node_count = graph_service.build_graph_nodes()
        graph_edge_count = graph_service.build_graph_edges()

        conn.commit()

        # Return plain dict to avoid any positional BaseModel init issues
        return {
            "message": "Ingestion completed successfully",
            "relational_tables": relational_counts,
            "graph_nodes": graph_node_count,
            "graph_edges": graph_edge_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    finally:
        if conn is not None:
            conn.close()