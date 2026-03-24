from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from ..services.query_service import QueryService

router = APIRouter(prefix="/api/query", tags=["query"])


@router.get("/top-products")
def get_top_products(limit: int = Query(10, ge=1, le=100)) -> Dict[str, Any]:
    try:
        service = QueryService()
        return service.top_products_by_billing_count(limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/broken-flows")
def get_broken_flows() -> Dict[str, Any]:
    try:
        service = QueryService()
        return service.broken_flows()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.get("/trace/billing/{billing_document_id}")
def trace_billing_flow(billing_document_id: str) -> Dict[str, Any]:
    try:
        service = QueryService()
        return service.trace_billing_flow(billing_document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")