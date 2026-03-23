"""Graph exploration router."""

from fastapi import APIRouter, HTTPException
from typing import Optional
from ..schemas import (
    SchemaResponse, GraphOverviewResponse,
    NodeResponse, SubgraphResponse
)
from ..services.graph_service import GraphService
from ..db.duckdb import db

router = APIRouter()
graph_service = GraphService()


@router.get("/schema", response_model=SchemaResponse)
async def get_schema():
    """Get database schema information."""
    try:
        relational_tables = [table for table in db.get_table_names() if not table.startswith('graph_')]
        graph_nodes_count = db.get_table_count('graph_nodes')
        graph_edges_count = db.get_table_count('graph_edges')

        return SchemaResponse(
            relational_tables=relational_tables,
            graph_nodes_count=graph_nodes_count,
            graph_edges_count=graph_edges_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")


@router.get("/graph/overview", response_model=GraphOverviewResponse)
async def get_graph_overview():
    """Get graph overview with counts and samples."""
    try:
        node_counts = graph_service.get_node_counts()
        edge_counts = graph_service.get_edge_counts()
        sample_nodes = graph_service.get_sample_nodes()
        sample_edges = graph_service.get_sample_edges()

        return GraphOverviewResponse(
            node_counts=node_counts,
            edge_counts=edge_counts,
            sample_nodes=sample_nodes,
            sample_edges=sample_edges
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get graph overview: {str(e)}")


@router.get("/node/{node_id}", response_model=NodeResponse)
async def get_node(node_id: str):
    """Get a specific node with its neighbors."""
    try:
        result = graph_service.get_node_with_neighbors(node_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

        return NodeResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get node: {str(e)}")


@router.get("/graph/subgraph", response_model=SubgraphResponse)
async def get_subgraph(node_id: str, depth: int = 1):
    """Get a subgraph around a node."""
    try:
        if depth < 1 or depth > 2:
            raise HTTPException(status_code=400, detail="Depth must be 1 or 2")

        result = graph_service.get_subgraph(node_id, depth)
        return SubgraphResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get subgraph: {str(e)}")