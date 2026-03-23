# System Architecture

## High-Level Data Flow

```
User Input (NL Query)
    ↓
Frontend Chat Interface
    ↓
API Request → FastAPI Backend
    ↓
Intent Classification (Graph vs Analytical)
    ↓
SQL Generation & Validation
    ↓
DuckDB Query Execution (21K rows across 19 JSONL-sourced tables)
    ↓
LLM Response Synthesis
    ↓
Return grounded response with evidence
    ↓
Render in Frontend (chat + graph highlight)

## Component Details

### Frontend (React + Vite + React Flow)

**Stack**
- React 18 with Vite bundler
- TypeScript for type safety
- React Flow for interactive graph visualization
- TanStack Query for API state management

**Responsibilities**
- Render interactive node-link diagram
- Accept natural language chat input
- Display grounding evidence (highlighted nodes/edges)
- Show node details on demand
- Manage filter state (date range, status, supplier)

**State Management**
- Local React state for UI (expanded panes, selected nodes)
- React Query cache for API responses
- Chat history in-memory + persisted to localStorage

### Backend (FastAPI + DuckDB)

**HTTP Server**
- FastAPI with async route handlers
- CORS enabled for frontend domain
- Request validation via Pydantic

**Route Structure**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/graph/nodes` | Fetch all nodes, optionally filtered |
| GET | `/api/graph/edges` | Fetch edges (explicit traversals) |
| GET | `/api/node/{id}/details` | Fetch node + related context |
| GET | `/api/schema` | Table schemas (for LLM context) |
| POST | `/api/chat` | Natural language query + chat state |
| GET | `/api/health` | Liveness check |

**Request/Response Contracts**
See `docs/api-contract.md` for detailed schemas.

**Core Services**

1. **QueryService**
   - SQL builder using SQLAlchemy
   - Query optimization (index hints, result limits)
   - Timeout enforcement

2. **GraphService**
   - Edge projection logic
   - Traversal algorithms (BFS, DFS)
   - Node ranking / relevance scoring

3. **LLMService**
   - SQL generation from natural language
   - Response synthesis from query results
   - Out-of-domain detection

4. **ValidationService**
   - SQL AST parsing and inspection
   - Input sanitization
   - Output schema verification

### Data Layer (DuckDB + Graph Projection)

**Why DuckDB?**

| Aspect | Why DuckDB | Alternatives |
|--------|-----------|--------------|
| **Deployment** | Single file, no server | PostgreSQL = ops overhead |
| **SQL Power** | Rich JOIN/WINDOW/ARRAY support | SQLite = limited functions |
| **Analytical** | Vectorized execution, fast aggregation | MySQL/PG = OLTP-optimized |
| **Distribution** | Perfect for assignments | Not cloud-native (feature) |
| **Python Integration** | Native, zero-copy | External services = latency |

**Schema Structure**

Raw tables (from SAP export):
```
Orders (order_id, customer_id, supplier_id, created_date, ...)
OrderItems (item_id, order_id, material_id, quantity, ...)
Fulfillments (fulfillment_id, item_id, received_qty, received_date, ...)
Invoices (invoice_id, order_id, amount, invoice_date, ...)
Payments (payment_id, invoice_id, amount, payment_date, ...)
Suppliers (supplier_id, name, location, ...)
Materials (material_id, description, category, ...)
Plants (plant_id, name, location, ...)
```

**Graph Projection (Query-Time)**

Instead of pre-materializing a graph database, we project edges dynamically:

```sql
-- Example: Trace single order from creation to payment
SELECT 
  'order' as source_type, o.order_id as source_id,
  'invoice' as target_type, i.invoice_id as target_id,
  'INVOICED_IN' as edge_type
FROM Orders o
JOIN OrderItems oi ON o.order_id = oi.order_id
JOIN Invoices i ON i.order_id = o.order_id
WHERE o.order_id = $1
```

**Benefits of Projection Over Materialized Graph**
- Schema flexibility (add relationships without re-materialization)
- Lower storage footprint (no edge duplication)
- Query-time filtering (only materialize relevant edges)
- Consistency guaranteed (always fresh from source)

## Data Flow Examples

### Example 1: Graph Exploration (User clicks "Show related orders")

```
Frontend → GET /api/graph/edges?source_type=supplier&source_id=123
  ↓
QueryService builds SQL to fetch all supplier → order edges
  ↓
DuckDB executes projection query
  ↓
Response: [
    { source: "supplier:123", target: "order:456", edge_type: "SUPPLIES" },
    { source: "supplier:123", target: "order:789", edge_type: "SUPPLIES" }
]
  ↓
Frontend renders new nodes and edges in React Flow canvas
```

### Example 2: Natural Language Query (User asks "Which orders are overdue?")

```
Frontend → POST /api/chat { message: "Which orders are overdue?", history: [...] }
  ↓
LLMService classifies: Analytical query (not graph traversal)
  ↓
SQL Generation: 
  "SELECT order_id, created_date FROM Orders 
   WHERE DATEDIFF(day, created_date, NOW()) > 30 
   AND status != 'completed'"
  ↓
ValidationService checks:
  - Only SELECT? ✓
  - Joins allowed? ✓
  - Result limit? (set LIMIT 1000)
  ✓ Safe to execute
  ↓
QueryService executes SQL with 5s timeout
  ↓
Result: { rows: [{order_id: 456, ...}, ...], count: 42 }
  ↓
LLMService synthesizes:
  "Found 42 orders that are overdue by >30 days. Order #456 
   was created on [date]. Would you like details on any specific order?"
  ↓
Frontend displays response + highlights relevant nodes
```

### Example 3: Out-of-Domain Detection (User asks "What's the capital of France?")

```
Frontend → POST /api/chat { message: "What's the capital of France?", ... }
  ↓
LLMService semantic check: Not mentioning order/supplier/payment/etc
  ↓
Fallback: Return hardcoded response
  "This system is designed to answer questions related to 
   the provided dataset only."
  ↓
Frontend shows response in chat
```

## Query Routing Decision Tree

```
User NL Query
    ↓
Is it about the dataset? (semantic check)
    ├─ NO → Reject with scope message
    └─ YES
        ↓
Can it be answered with graph traversal?
    ├─ YES (e.g., "Show orders from Supplier X")
       → Use GraphService.traverse()
    └─ NO
        ↓
Generate SQL for analytical query
    ├─ If valid → Execute, synthesize response
    └─ If invalid → Reject with explanation
```

## Performance Optimization

**Query Level**
- Index all foreign keys and common WHERE columns
- Pre-compute summary tables (daily aggregations) if needed
- Prepared statements to prevent parsing overhead

**Result Level**
- Limit node/edge queries to 500 results default
- Pagination token for large result sets
- Lazy-load node details only when expanded

**Frontend Level**
- React Query cache with 5-min TTL
- Debounce filter inputs (500ms)
- Virtual scrolling for large edge lists

## Security & Validation

**Layered Validation**
1. **Input**: Request schema + size limits
2. **Query**: SQL AST inspection + allowlist
3. **Execution**: Timeout + result limits
4. **Output**: Schema validation before response

**Dangerous Patterns Blocked**
- No INSERT/UPDATE/DELETE
- No TRUNCATE
- No access to system tables
- No dynamic SQL execution
- No file system access

**Scope Guarding**
- System prompt explicitly defines allowable topics
- Semantic relevance check before SQL generation
- Fallback responses for ambiguous queries

## Deployment Architecture

**Frontend: Vercel**
- Auto-deployed on push to `main`
- Environment: `VITE_API_URL` points to backend
- CDN-distributed, HTTPS enforced

**Backend: Render**
- Gunicorn + FastAPI
- Environment: `DATABASE_PATH` points to DuckDB file
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`

**Data: Included in Backend**
- DuckDB file committed to repo (or fetched in deploy)
- Size constraint: < 500MB for Render deployment
- Backup: Versioned in Git LFS if needed

See `docs/deployment.md` for detailed setup.

## Testing Strategy

**Unit Tests** (80%+ coverage)
- SQL builder correctness
- Validation logic
- Graph projection accuracy

**Integration Tests**
- End-to-end API flows
- DuckDB + LLM grounding verification
- Rejection cases

**Manual Testing**
- Graph exploration UX
- Chat responsiveness
- Out-of-domain rejection

---

## Key Design Decisions

| Decision | Rationale | Tradeoff |
|----------|-----------|----------|
| Graph projection, not materialized DB | Flexibility, consistency | Slightly slower joins |
| DuckDB, not PostgreSQL | Simplicity, embedded | Single-process, no replication |
| FastAPI over Flask | Type safety, async | Slightly heavier framework |
| React Flow over D3 | Interactivity, accessibility | Less customization |
| LLM for SQL generation | More natural queries | Hallucination risk (mitigated by validation) |
| Read-only SQL only | Safety | Limits future features (logging updates) |
