#!/usr/bin/env python3
"""Test database initialization."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db.init_db import create_relational_tables, create_graph_tables

print("Creating tables...")
create_relational_tables()
create_graph_tables()
print("Tables created successfully")