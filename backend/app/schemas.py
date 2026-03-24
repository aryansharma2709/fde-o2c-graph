"""Pydantic schemas for API requests and responses."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"


class IngestResponse(BaseModel):
    """Ingestion response with counts."""
    relational_tables: Dict[str, int]
    graph_nodes: int
    graph_edges: int
    message: str


class SchemaResponse(BaseModel):
    """Schema information response."""
    relational_tables: List[str]
    graph_nodes_count: int
    graph_edges_count: int


class GraphOverviewResponse(BaseModel):
    """Graph overview with counts and samples."""
    node_counts: Dict[str, int]
    edge_counts: Dict[str, int]
    sample_nodes: List[Dict[str, Any]]
    sample_edges: List[Dict[str, Any]]


class NodeDetail(BaseModel):
    """Node with metadata."""
    node_id: str
    node_type: str
    label: str
    metadata: Dict[str, Any]


class EdgeDetail(BaseModel):
    """Edge with metadata."""
    edge_id: str
    source_id: str
    target_id: str
    edge_type: str
    metadata: Dict[str, Any]


class NodeResponse(BaseModel):
    """Single node response with neighbors."""
    node: NodeDetail
    incoming_edges: List[EdgeDetail]
    outgoing_edges: List[EdgeDetail]
    neighbors: List[NodeDetail]


class SubgraphResponse(BaseModel):
    """Subgraph response for neighborhood."""
    nodes: List[NodeDetail]
    edges: List[EdgeDetail]