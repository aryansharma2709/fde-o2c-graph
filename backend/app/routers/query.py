from fastapi import APIRouter, Query, HTTPException
from typing import Any
from ..db.connection import get_db_connection
from ..services.query_service import QueryService

router = APIRouter(prefix="/api/query")

@router.get("/top-products")
def top_products(limit: int = Query(10, ge=1, le=100)) -> Any:
    try:
        conn = get_db_connection()
        service = QueryService(conn)
        results = service.top_products_by_billing_count(limit)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/trace/billing/{billing_document_id}")
def trace_billing(billing_document_id: str) -> Any:
    conn = get_db_connection()
    service = QueryService(conn)
    return service.trace_billing_flow(billing_document_id)

@router.get("/broken-flows")
def broken_flows() -> Any:
    conn = get_db_connection()
    service = QueryService(conn)
    return service.broken_flows()
