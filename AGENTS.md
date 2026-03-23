# Architecture & Design Decisions

## Overview

This system is a **graph-based Order-to-Cash data explorer** with a grounded LLM chat interface. It enables natural language questions about SAP-style procurement, fulfillment, and finance data while maintaining strict boundaries on query scope and data safety.

## Design Philosophy

- **Simplicity over complexity**: Explainable graph projections, not opaque embeddings
- **Safety-first**: All LLM answers are grounded in validated dataset queries
- **Modularity**: Clean separation of concerns across layers
- **Production-ready**: Code style follows industry standards from day one

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│         React + Vite + TypeScript + Flow    │  Frontend
├─────────────────────────────────────────────┤
│          FastAPI + Pydantic + SQLAlchemy   │  Backend
├─────────────────────────────────────────────┤
│      DuckDB + Graph Projection Layer       │  Data
└─────────────────────────────────────────────┘
```

## Frontend Stack

- **React + Vite**: Fast HMR, minimal build overhead, TypeScript first
- **React Flow**: Interactive graph visualization and exploration
- **TypeScript**: Type safety, better IDE support, refactoring confidence
- **API Client**: Minimal wrapper around fetch, not over-engineered

### Responsibilities
- Render interactive graph (orders, items, fulfillments, invoices, payments)
- Visual trace of query results with node details pane
- Chat interface with validated message history
- Real-time document indicators for grounding evidence

## Backend Stack

- **FastAPI**: Async request handling, auto-generated docs, minimal boilerplate
- **Pydantic**: Schema validation, serialization, clear contracts
- **SQLAlchemy**: Safe ORM layer for DuckDB, query builders
- **DuckDB**: In-process OLAP database, perfect for analytical queries on tabular SAP data

### Responsibilities
- REST API for graph queries (nodes, edges, traversals)
- Natural language → SQL translation via LLM
- Query validation and execution against DuckDB
- Chat state management and response generation

## Data Layer

### Why DuckDB + Graph Projection

**DuckDB advantages for this use case:**
1. In-process → no deployment complexity (vs. PostgreSQL)
2. Excellent SQL support → complex O2C joins trivial
3. Fast analytical queries → instant graph projections
4. Deterministic → perfect for reproducible grounding
5. File-based → easy distribution in take-home assignment

**Graph projection over relational data:**
- **Not a graph database**: SAP data is inherently relational (tables, foreign keys)
- **Graph projection**: Transform normalized tables into explicit edge lists dynamically
  - Order → OrderItem → Fulfillment → Invoice → Payment (trace traversal)
  - Order → Supplier (relationships)
  - Item → Material (product relationships)
- **Benefits**: Query-time generation vs. pre-materialized paths; schema flexibility; easy to add new relationships

### Core Node Types
- `Order` (header level)
- `OrderItem` (line level)
- `Fulfillment`, `Receipt`, `Invoice`, `Payment`
- `Supplier`, `Material`, `Plant`

### Core Edge Types
- `INCLUDES` (Order → OrderItem)
- `FULFILLED_BY` (OrderItem → Fulfillment)
- `INVOICED_IN` (OrderItem → Invoice)
- `PAID_BY` (Invoice → Payment)
- `SUPPLIED_BY` (Order → Supplier)
- `IS_MATERIAL` (OrderItem → Material)

## LLM Integration & Grounding

### Query Classification
1. **NL → Intent parsing**: Determine if graph traversal or analytical query
   - "Show me orders from Supplier X" → Graph traversal
   - "What's the average payment delay?" → Analytical query

2. **SQL Generation**: LLM generates candidate SQL from table schemas
   - Receives: table names, columns, data types, sample rows (no sensitive PII)
   - Returns: SELECT statement only (no INSERT/UPDATE/DELETE)

3. **Validation Layer**:
   ```python
   - Reject non-SELECT statements
   - Reject joins outside allowlist
   - Limit result set to N rows
   - Timeout queries after T seconds
   - Validate output schema before returning
   ```

4. **Response Generation**: LLM synthesizes findings from query results
   - "Based on the query results, Order #123 was fulfilled by..."
   - Evidence includes: actual row count, key values, aggregations

### Out-of-Domain Rejection
```
User: "What's the weather in NYC?"
System: "This system is designed to answer questions related to 
         the provided dataset only."
```

Implemented via:
- System prompt: explicit scope definition
- Input validation: semantic relevance check
- Fallback responses: hardcoded for known off-topic patterns

## API Contract

See `docs/api-contract.md` for detailed endpoint specifications.

**Key endpoints:**
- `GET /api/graph/nodes` → fetch nodes with filters
- `GET /api/graph/edges` → fetch edges (traversals)
- `GET /api/node/{id}/details` → node data + related context
- `POST /api/chat` → natural language query with grounding

## Guardrails & Safety

1. **SQL Validation**: Parse and inspect query AST before execution
2. **Query Timeouts**: All queries terminate after 5 seconds
3. **Result Limits**: Return at most 1000 rows to prevent data exfiltration
4. **Read-Only Mode**: All SQL operations are SELECT only
5. **Scope Checking**: LLM system prompt explicitly defines domain
6. **Input Sanitization**: No prompt injection via structured extraction

## Code Organization

```
backend/
├── app/
│   ├── main.py              # FastAPI app, routes
│   ├── models/              # Pydantic schemas
│   ├── queries/             # SQL builders, graph logic
│   ├── services/            # Business logic, LLM integration
│   ├── utils/               # Validation, safety checks
│   └── config.py            # Settings, environment
├── data/
│   └── schema.sql           # DuckDB DDL
└── tests/
    ├── test_queries.py
    ├── test_validation.py
    └── test_llm_grounding.py

frontend/
├── src/
│   ├── components/
│   │   ├── GraphView.tsx    # React Flow canvas
│   │   ├── ChatPanel.tsx    # Chat interface
│   │   ├── NodeDetails.tsx  # Side pane details
│   │   └── ControlPanel.tsx # Filters, search
│   ├── services/
│   │   └── api.ts           # API client
│   ├── types/
│   │   └── index.ts         # Shared TypeScript types
│   ├── App.tsx
│   └── main.tsx
└── package.json
```

## Evaluation Criteria Focus

1. **Code Quality**: Modular, testable, no duplication
2. **Graph Modeling**: Clear entity relationships, efficient traversals
3. **Storage Choice**: DuckDB justified; no unnecessary columns
4. **LLM Prompting**: Structured extraction, explicit scope
5. **Guardrails**: Comprehensive validation, clear failure modes

## Bonus Features (Deep Implementation)

- **Anomaly Detection**: Identify unusual payment delays, receipt gaps
- **Query History**: Replay past queries, compare results over time
- **Data Lineage**: Show transformation steps from raw table to result
- **Custom Traversals**: User-defined graph patterns (order → all related payments)
- **Performance Tracing**: Show query execution time, data freshness
- **Incremental Export**: Download query results as CSV/JSON

---

## Key Constraints

- **No external dependencies** beyond core stack (FastAPI, DuckDB, React, LLM API)
- **Reproducibility**: All answers must be reproducible from dataset queries
- **Latency**: Chat responses within 2 seconds
- **Safety**: 100% query rejection rate for out-of-scope prompts (in testing)
