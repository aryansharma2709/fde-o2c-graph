"""FastAPI application for O2C Graph Explorer backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers.health import router as health_router
from .routers.ingest import router as ingest_router
from .routers.graph import router as graph_router
from .db.init_db import init_database

# Initialize database on startup
init_database()

app = FastAPI(
    title="O2C Graph Explorer API",
    description="Backend API for SAP Order-to-Cash graph exploration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(ingest_router, prefix="/api", tags=["ingestion"])
app.include_router(graph_router, prefix="/api", tags=["graph"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "O2C Graph Explorer API", "version": "1.0.0"}