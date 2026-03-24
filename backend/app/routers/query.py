
from fastapi import APIRouter, Query, HTTPException
from typing import Any
from ..db.connection import get_db_connection
from ..services.query_service import QueryService

router = APIRouter(prefix="/api/query")

@router.get("/top-products")

def top_products(limit: int = Query(10, ge=1, le=100)) -> Any:
    try:
        service = QueryService()
        results = service.top_products_by_billing_count(limit)
        return {"results": results}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/trace/billing/{billing_document_id}")

def trace_billing(billing_document_id: str) -> Any:
    try:
        service = QueryService()
        return service.trace_billing_flow(billing_document_id)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/broken-flows")

def broken_flows() -> Any:
    try:
        service = QueryService()
        return service.broken_flows()
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
