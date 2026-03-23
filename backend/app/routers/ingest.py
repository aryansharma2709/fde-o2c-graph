"""Ingestion router."""

from fastapi import APIRouter, HTTPException
from ..schemas import IngestResponse
from ..services.ingest_service import IngestService
from ..services.graph_service import GraphService
from ..db.duckdb import db

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_dataset():
    """Ingest the SAP O2C dataset and build graph projections."""
    try:
        # Clear existing data
        ingest_service = IngestService()
        ingest_service.clear_tables()

        # Ingest relational data
        relational_counts = ingest_service.ingest_all_collections()

        # Build graph projections
        graph_service = GraphService()
        node_count = graph_service.build_graph_nodes()
        edge_count = graph_service.build_graph_edges()

        return IngestResponse(
            relational_tables=relational_counts,
            graph_nodes=node_count,
            graph_edges=edge_count,
            message="Dataset ingested successfully"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")