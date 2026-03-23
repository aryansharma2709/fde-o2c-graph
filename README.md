# O2C Graph Explorer: Order-to-Cash Data Explorer with Grounded LLM Chat

A take-home assignment for Forward Deployed Engineers. A graph-based data explorer over a SAP-style Order-to-Cash dataset with natural language querying backed by validated SQL.

## Overview

This system combines:
- **Interactive graph visualization** (React Flow) for exploring order relationships
- **Natural language queries** with an LLM that generates SQL
- **Grounded responses** where every answer is verified against actual query results
- **Safety guardrails** ensuring queries are read-only, scoped, and validated

**Stack**: 
- **Frontend**: React 18 + Vite + TypeScript + React Flow
- **Backend**: FastAPI + Pydantic + SQLAlchemy
- **Data**: DuckDB with graph projection from relational tables

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- DuckDB database file at `data/sap-orders.duckdb` (or generate from raw zip)

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Load dataset (if not already present)
unzip data/raw/sap-order-to-cash-dataset.zip -d data/raw/
python scripts/load_dataset.py

# Start dev server
uvicorn app.main:app --reload --port 8000

# View docs at http://localhost:8000/docs
```

### Frontend (React + Vite)

```bash
cd frontend
npm install

# Create .env.development.local
echo "VITE_API_URL=http://localhost:8000" > .env.development.local

# Start dev server
npm run dev

# Visit http://localhost:5173
```

## Architecture at a Glance

```
User Query (NL)
    ↓
Frontend (React Flow graph + chat)
    ↓
Backend (FastAPI)
    ├→ Intent Classification (graph traversal or analytics)
    ├→ SQL Generation (LLM) + Validation
    ├→ DuckDB Execution (projected graph)
    └→ Response Synthesis (grounded in results)
    ↓
Response + Grounding Evidence (query, rows, execution time)
```

### Why DuckDB + Graph Projection?

- **DuckDB**: In-process OLAP database. Perfect for SAP relational data, fast analytical queries, no deployment overhead.
- **Graph Projection**: Transform normalized tables into edges on-query-time. Flexible schema, consistency guaranteed, lower storage.
- **LLM Grounding**: All answers backed by validated SELECT queries executed against DuckDB. No hallucination.

### Safety First

- ✅ **Read-only SQL** (SELECT only, no INSERT/UPDATE/DELETE)
- ✅ **Query validation** (AST inspection, allowlist joins)
- ✅ **Timeout enforcement** (5s max per query)
- ✅ **Result limits** (1000 rows default)
- ✅ **Out-of-domain detection** (rejects weather, math, etc.)
- ✅ **Input sanitization** (prevents SQL injection, prompt injection)

## Documentation

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | Architecture decisions, design philosophy, constraints |
| [docs/architecture.md](docs/architecture.md) | System design, data flow, query routing, performance optimization |
| [docs/data-model.md](docs/data-model.md) | Dataset schema, node/edge types, join paths, query coverage |
| [docs/api-contract.md](docs/api-contract.md) | REST API endpoints, request/response schemas, error handling |
| [docs/deployment.md](docs/deployment.md) | Vercel frontend, Render backend, CI/CD, monitoring |
| [docs/demo-script.md](docs/demo-script.md) | 5-10 min demo flow showcasing graph, tracing, ranking, anomalies, guardrails |

## Key Features

### 1. Graph Exploration
- Interactive visualization of orders, suppliers, fulfillments, invoices, payments
- Click nodes for details, filter by supplier/date/status
- Edges show relationships: INCLUDES, FULFILLED_BY, INVOICED_IN, PAID_BY, SUPPLIED_BY

### 2. Trace Queries
Ask: "Trace Order #123 from creation to payment"  
System traces O2C lifecycle, shows all intermediate nodes, highlights path in graph

### 3. Ranking Queries
Ask: "Top 5 slowest orders by O2C time this month"  
System aggregates dates, calculates cycle time, ranks results

### 4. Anomaly Detection
Ask: "Show invoices with duplicate payments"  
System detects data quality issues, highlights anomalies

### 5. Guardrail Rejection
Ask: "What's the weather?"  
System: "This system is designed to answer questions related to the provided dataset only."

## Project Structure

```
├── AGENTS.md                          # Design & decision doc
├── README.md                          # This file
├── docs/
│   ├── architecture.md                # System design
│   ├── data-model.md                  # Schema & data types
│   ├── api-contract.md                # REST API spec
│   ├── deployment.md                  # Deploy guide
│   └── demo-script.md                 # Demo walkthrough
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, routes (TO BUILD)
│   │   ├── models/                    # Pydantic schemas
│   │   ├── queries/                   # SQL builders, graph logic
│   │   ├── services/                  # Business logic, LLM integration
│   │   ├── utils/                     # Validation, sanitization
│   │   └── config.py                  # Settings, env
│   ├── tests/                         # Unit & integration tests
│   ├── data/
│   │   ├── schema.sql                 # DuckDB DDL
│   │   └── sap-orders.duckdb          # Data file
│   ├── scripts/
│   │   ├── load_dataset.py            # Unzip & import to DuckDB
│   │   └── create_indices.py          # Optimize queries
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── GraphView.tsx          # React Flow canvas (TO BUILD)
│   │   │   ├── ChatPanel.tsx          # Chat interface
│   │   │   ├── NodeDetails.tsx        # Side pane
│   │   │   └── ControlPanel.tsx       # Filters
│   │   ├── services/
│   │   │   └── api.ts                 # API client
│   │   ├── types/
│   │   │   └── index.ts               # TypeScript types
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile.dev
├── data/
│   └── raw/
│       └── sap-order-to-cash-dataset.zip    # Source data
└── scripts/
    ├── load_dataset.py
    └── create_indices.py
```

## Development Workflow

### 1. Data Exploration
```bash
# Unzip & load dataset
unzip data/raw/sap-order-to-cash-dataset.zip -d data/raw/
python scripts/load_dataset.py

# Verify schema
python -c "import duckdb; print(duckdb.connect('data/sap-orders.duckdb').execute('SHOW TABLES').fetchall())"
```

### 2. Backend Implementation
```bash
# Install deps
cd backend
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Dev server (auto-reload)
uvicorn app.main:app --reload
```

### 3. Frontend Implementation
```bash
# Install deps
cd frontend
npm install

# Dev server (HMR)
npm run dev

# Build for prod
npm run build
```

### 4. Testing
```bash
# Backend unit tests
pytest backend/tests/ -v

# Frontend component tests
npm run test

# Integration tests (both running)
curl http://localhost:8000/api/graph/nodes
```

## Deployment

### Frontend → Vercel
```bash
git push origin main  # Auto-triggers Vercel deploy
# or
vercel deploy --prod
```

Visit: https://fde-o2c-graph.vercel.app

### Backend → Render
```bash
# Set env vars in Render dashboard
DATABASE_PATH=data/sap-orders.duckdb
OPENAI_API_KEY=sk-...
ENVIRONMENT=production

# Push to main triggers auto-deploy
git push origin main
```

Visit: https://fde-o2c-graph-backend.render.com/api/health

See [docs/deployment.md](docs/deployment.md) for detailed setup.

## Demo

Ready to see it in action?

```bash
# Start backend
cd backend && python -m uvicorn app.main:app --reload

# Start frontend (new terminal)
cd frontend && npm run dev

# Visit http://localhost:5173
# Try queries:
# - "Trace Order #ORD-2026-001 from creation to payment"
# - "Top 5 slowest orders by O2C time"
# - "Show invoices with duplicate payments"
```

See [docs/demo-script.md](docs/demo-script.md) for a full 5-10 min walkthrough.

## Evaluation Criteria

This implementation focuses on:

1. **Code Quality**: Modular, testable, production-ready
2. **Graph Modeling**: Clear O2C entity relationships, efficient traversals
3. **Storage Choice**: DuckDB justified; no unnecessary columns
4. **LLM Prompting**: Structured extraction, explicit scope, validation before execution
5. **Guardrails**: Comprehensive SQL validation, read-only enforcement, clear failure modes

## Bonus Features (Deep Implementation)

- 🔍 **Query History**: Replay past queries, compare results over time
- 📊 **Anomaly Detection**: Identify unusual payment delays, fulfillment gaps
- 🔗 **Data Lineage**: Show transformation steps from raw table to result
- 🎯 **Custom Traversals**: User-defined graph patterns (order → all related payments)
- ⏱️ **Performance Tracing**: Query execution time, data freshness
- 📥 **Incremental Export**: Download results as CSV/JSON

## Contributing

This is a take-home assignment. For evaluation feedback, see `AGENTS.md` and `docs/`.

## License

MIT (assignment submission)

---

**Status**: 🚧 Under construction  
**Next**: Backend implementation, frontend components, integration tests
