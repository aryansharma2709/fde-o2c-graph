from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from ..services.graph_service import GraphService

router = APIRouter()

router = APIRouter()


@router.get("/schema")
def get_schema() -> Dict[str, Any]:
    """Return relational table names and graph table counts."""
    try:
        service = GraphService()

        relational_tables = [
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

        table_counts = {}
        for table in relational_tables:
            try:
                row = service.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                table_counts[table] = int(row[0]) if row else 0
            except Exception:
                table_counts[table] = 0

        graph_nodes = 0
        graph_edges = 0

        try:
            row = service.conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()
            graph_nodes = int(row[0]) if row else 0
        except Exception:
            pass

        try:
            row = service.conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()
            graph_edges = int(row[0]) if row else 0
        except Exception:
            pass

        return {
            "relational_tables": table_counts,
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {e}")


@router.get("/graph/overview")
def get_graph_overview() -> Dict[str, Any]:
    """Get graph overview with counts and samples."""
    try:
        service = GraphService()
        return service.get_graph_overview()
    except Exception as e:
        message = str(e)
        if "graph_nodes" in message or "graph_edges" in message:
            raise HTTPException(
                status_code=409,
                detail="Graph not built yet. Run /api/ingest first.",
            )
        raise HTTPException(status_code=500, detail=f"Failed to get graph overview: {e}")


@router.get("/node/{node_id}")
def get_node(node_id: str) -> Dict[str, Any]:
    """Get one node, its immediate edges, and neighboring nodes."""
    try:
        service = GraphService()
        result = service.get_node_with_neighbors(node_id)
        if not result:
            raise HTTPException(status_code=404, detail="Node not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node details: {e}")


@router.get("/graph/subgraph")
def get_subgraph(node_id: str = Query(...), depth: int = Query(1, ge=1, le=2)) -> Dict[str, Any]:
    """Get a neighborhood subgraph around a node."""
    try:
        service = GraphService()
        return service.get_subgraph(node_id, max_depth=depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subgraph: {e}")