# API Contract

## Base URL

```
Development: http://localhost:8000
Production: https://fde-o2c-graph-backend.render.com
```

## Authentication

Currently: None (assume same-origin or CORS-protected deployment)

Future: Bearer token or API key if needed.

---

## Endpoints

### 1. Health Check

```http
GET /api/health
```

**Response (200 OK)**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### 2. Ingest Dataset

Load the SAP O2C dataset and build graph projections.

```http
POST /api/ingest
```

**Response (200 OK)**
```json
{
  "relational_tables": {
    "sales_order_headers": 100,
    "sales_order_items": 167,
    ...
  },
  "graph_nodes": 1234,
  "graph_edges": 5678,
  "message": "Dataset ingested successfully"
}
```

---

### 3. Get Schema

Get database schema information.

```http
GET /api/schema
```

**Response (200 OK)**
```json
{
  "relational_tables": [
    "sales_order_headers",
    "sales_order_items",
    ...
  ],
  "graph_nodes_count": 1234,
  "graph_edges_count": 5678
}
```

---

### 4. Get Graph Overview

Get graph statistics and samples.

```http
GET /api/graph/overview
```

**Response (200 OK)**
```json
{
  "node_counts": {
    "Customer": 8,
    "SalesOrder": 100,
    ...
  },
  "edge_counts": {
    "CUSTOMER_PLACED_ORDER": 100,
    ...
  },
  "sample_nodes": [
    {
      "node_id": "Customer:310000108",
      "node_type": "Customer",
      "label": "Customer ABC Corp"
    }
  ],
  "sample_edges": [
    {
      "edge_id": "CUSTOMER_PLACED_ORDER:740506",
      "edge_type": "CUSTOMER_PLACED_ORDER",
      "source_id": "Customer:310000108",
      "target_id": "SalesOrder:740506"
    }
  ]
}
```

---

### 5. Get Node Details

Get a specific node with its immediate neighbors.

```http
GET /api/node/{node_id}
```

**Path Parameters**
| Param | Type | Description |
|-------|------|-------------|
| `node_id` | string | Node ID (e.g., "SalesOrder:740506") |

**Response (200 OK)**
```json
{
  "node": {
    "node_id": "SalesOrder:740506",
    "node_type": "SalesOrder",
    "label": "740506",
    "metadata": {
      "totalNetAmount": 17108.25,
      "creationDate": "2025-03-31T00:00:00.000Z"
    }
  },
  "incoming_edges": [...],
  "outgoing_edges": [...],
  "neighbor_nodes": [...]
}
```

**Response (404 Not Found)**
```json
{
  "detail": "Node SalesOrder:740506 not found"
}
```

---

### 6. Get Subgraph

Get a neighborhood subgraph around a node.

```http
GET /api/graph/subgraph?node_id=SalesOrder:740506&depth=1
```

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `node_id` | string | required | Center node ID |
| `depth` | int | 1 | Traversal depth (1-2) |

**Response (200 OK)**
```json
{
  "nodes": [...],
  "edges": [...],
  "center_node_id": "SalesOrder:740506",
  "depth": 1
}
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 422 | Unprocessable entity (validation error) |
| 429 | Rate limited |
| 500 | Server error |
| 503 | Service unavailable (database error) |

---

## Error Response Format

All errors follow this format:

```json
{
  "error": "error_code",
  "detail": "Human-readable explanation",
  "request_id": "req-xyz-123"
}
```

---

## CORS Policy

```
Allowed Origins: https://fde-o2c-graph.vercel.app, http://localhost:3000
Allowed Methods: GET, POST, OPTIONS
Allowed Headers: Content-Type, Authorization
Credentials: true (if using cookies)
```

---

## API Versioning

Current version: `v1` (implicit, may be added to paths in future)

Future breaking changes will use `/api/v2/*` paths.

---

## Testing

**cURL Examples**

```bash
# Health check
curl "http://localhost:8000/api/health"

# Ingest dataset
curl -X POST "http://localhost:8000/api/ingest"

# Get schema
curl "http://localhost:8000/api/schema"

# Get graph overview
curl "http://localhost:8000/api/graph/overview"

# Get node details
curl "http://localhost:8000/api/node/SalesOrder:740506"

# Get subgraph
curl "http://localhost:8000/api/graph/subgraph?node_id=SalesOrder:740506&depth=1"
```

---

## Implementation Notes

- All `node_id` fields are globally unique within their type (e.g., `SalesOrder:740506`)
- Node types use PascalCase (e.g., `SalesOrder`, `Customer`)
- Edge types use UPPER_SNAKE_CASE (e.g., `CUSTOMER_PLACED_ORDER`)
- Timestamps are ISO-8601 format, UTC timezone
- Monetary amounts are stored as DECIMAL for precision
- Null responses use `null` (not empty strings or 0)
        "supplier_id": "SUPP-123",
        "customer_id": "CUST-456"
      },
      "position": { "x": 0, "y": 0 }
    },
    {
      "id": "order_item:ITEM-001",
      "type": "order_item",
      "label": "ITEM-001",
      "attributes": {
        "order_id": "ORD-2026-001",
        "material_id": "MAT-789",
        "quantity": 100,
        "unit_price": 500.00
      },
      "position": { "x": 100, "y": 0 }
    }
  ],
  "pagination": {
    "total": 5420,
    "limit": 500,
    "offset": 0
  }
}
```

**Error (400 Bad Request)**
```json
{
  "error": "Invalid status filter",
  "detail": "Status must be one of: pending, completed, cancelled"
}
```

---

### 3. Get Graph Edges

Fetch edges (relationships) with optional filtering.

```http
GET /api/graph/edges?source_type=order&edge_type=INCLUDES&limit=500
```

**Query Parameters**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `source_type` | string | (required) | Source node type |
| `source_id` | string | (optional) | Filter to specific source node |
| `target_type` | string | (optional) | Target node type |
| `edge_type` | string | (all) | Filter by edge type (e.g., `INCLUDES`, `FULFILLED_BY`, `INVOICED_IN`, `PAID_BY`, `SUPPLIED_BY`) |
| `limit` | int | 500 | Result limit (max 1000) |
| `offset` | int | 0 | Result offset |

**Response (200 OK)**
```json
{
  "edges": [
    {
      "id": "edge:order:ORD-2026-001_order_item:ITEM-001",
      "source": "order:ORD-2026-001",
      "target": "order_item:ITEM-001",
      "type": "INCLUDES",
      "label": "includes",
      "animated": false
    },
    {
      "id": "edge:order_item:ITEM-001_fulfillment:FULF-001",
      "source": "order_item:ITEM-001",
      "target": "fulfillment:FULF-001",
      "type": "FULFILLED_BY",
      "label": "fulfilled by",
      "animated": false
    }
  ],
  "pagination": {
    "total": 12450,
    "limit": 500,
    "offset": 0
  }
}
```

**Error (400 Bad Request)**
```json
{
  "error": "Invalid edge_type",
  "detail": "Edge type must be one of: INCLUDES, FULFILLED_BY, INVOICED_IN, PAID_BY, SUPPLIED_BY, ORDERED_BY, USES_MATERIAL, PRODUCED_AT, SOURCES_FROM"
}
```

---

### 4. Get Node Details

Fetch detailed information about a single node, including related nodes.

```http
GET /api/node/order:ORD-2026-001/details
```

**Response (200 OK)**
```json
{
  "node": {
    "id": "order:ORD-2026-001",
    "type": "order",
    "label": "ORD-2026-001",
    "attributes": {
      "order_id": "ORD-2026-001",
      "created_date": "2026-01-15",
      "status": "completed",
      "total_amount": 50000.00,
      "supplier_id": "SUPP-123",
      "customer_id": "CUST-456"
    }
  },
  "related_nodes": {
    "items": [
      {
        "id": "order_item:ITEM-001",
        "type": "order_item",
        "label": "ITEM-001",
        "quantity": 100,
        "unit_price": 500.00
      }
    ],
    "invoices": [
      {
        "id": "invoice:INV-001",
        "type": "invoice",
        "label": "INV-001",
        "amount": 50000.00,
        "invoice_date": "2026-01-20"
      }
    ],
    "payments": [
      {
        "id": "payment:PAY-001",
        "type": "payment",
        "label": "PAY-001",
        "amount": 50000.00,
        "payment_date": "2026-02-15"
      }
    ],
    "supplier": {
      "id": "supplier:SUPP-123",
      "type": "supplier",
      "name": "Acme Corp",
      "location": "Singapore"
    }
  },
  "metrics": {
    "days_to_invoice": 5,
    "days_to_payment": 26,
    "total_o2c_days": 31
  }
}
```

**Error (404 Not Found)**
```json
{
  "error": "Node not found",
  "detail": "No node with ID 'order:INVALID-ID'"
}
```

---

### 5. Get Database Schema

Fetch table schemas for LLM context (used internally for SQL generation).

```http
GET /api/schema
```

**Response (200 OK)**
```json
{
  "tables": [
    {
      "name": "orders",
      "description": "Purchase orders",
      "columns": [
        {
          "name": "order_id",
          "type": "VARCHAR",
          "nullable": false,
          "description": "Unique order identifier"
        },
        {
          "name": "created_date",
          "type": "DATE",
          "nullable": false,
          "description": "Order creation date"
        },
        {
          "name": "status",
          "type": "VARCHAR",
          "nullable": true,
          "description": "Order status (pending, completed, cancelled)"
        },
        {
          "name": "total_amount",
          "type": "DECIMAL",
          "nullable": false,
          "description": "Total order amount"
        },
        {
          "name": "supplier_id",
          "type": "VARCHAR",
          "nullable": false,
          "description": "Foreign key to suppliers table"
        }
      ]
    }
  ],
  "joins": [
    {
      "left_table": "orders",
      "right_table": "order_items",
      "condition": "orders.order_id = order_items.order_id",
      "cardinality": "1:N"
    }
  ]
}
```

---

### 6. Chat / Natural Language Query

Submit a natural language question and receive a grounded response.

```http
POST /api/chat
Content-Type: application/json

{
  "message": "Which orders from Acme Corp are still pending?",
  "chat_id": "session-abc123",
  "history": [
    {
      "role": "user",
      "content": "Show me recent orders"
    },
    {
      "role": "assistant",
      "content": "Found 342 orders created in the last 7 days..."
    }
  ]
}
```

**Request Schema**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User's natural language question |
| `chat_id` | string | No | Session ID for multi-turn conversations |
| `history` | array | No | Previous turns in conversation |

**Response (200 OK)**
```json
{
  "chat_id": "session-abc123",
  "response": "Found 23 orders from Acme Corp that are still pending. The oldest pending order (#ORD-2025-432) was created on January 10, 2026. Would you like details on any specific order?",
  "grounding": {
    "query_type": "analytical",
    "sql_executed": "SELECT order_id, created_date, total_amount FROM orders WHERE supplier_id = 'SUPP-123' AND status = 'pending' ORDER BY created_date DESC LIMIT 1000",
    "result_count": 23,
    "execution_time_ms": 145,
    "highlighted_nodes": [
      "order:ORD-2025-432",
      "order:ORD-2025-433",
      "order:ORD-2025-434"
    ]
  }
}
```

**Error (400 Bad Request) - Out of Domain**
```json
{
  "error": "out_of_domain",
  "response": "This system is designed to answer questions related to the provided dataset only.",
  "grounding": {
    "reason": "Query does not reference SAP entities (orders, suppliers, invoices, etc.)"
  }
}
```

**Error (422 Unprocessable Entity) - Invalid Query**
```json
{
  "error": "invalid_query",
  "response": "I couldn't understand that question. Try asking about orders, suppliers, payments, or fulfillments.",
  "detail": "Failed to generate valid SQL from query intent"
}
```

**Error (500 Internal Server Error) - Query Timeout**
```json
{
  "error": "query_timeout",
  "response": "The query took too long to execute. Try narrowing your search (e.g., specific supplier or date range).",
  "grounding": {
    "execution_time_ms": 5001
  }
}
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid parameters) |
| 404 | Resource not found |
| 422 | Unprocessable entity (validation error) |
| 429 | Rate limited |
| 500 | Server error |
| 503 | Service unavailable (database error) |

---

## Rate Limiting

- **Endpoints**: `/api/graph/*` and `/api/node/*` (read-only)
  - Limit: 100 requests per minute per IP
  - Header: `X-RateLimit-Remaining`

- **Chat endpoint** (`/api/chat`)
  - Limit: 20 requests per minute per session
  - Reason: LLM API calls are expensive

---

## Error Response Format

All errors follow this format:

```json
{
  "error": "error_code",
  "detail": "Human-readable explanation",
  "request_id": "req-xyz-123"
}
```

---

## Pagination

Endpoints supporting large result sets use limit/offset pagination:

```
GET /api/graph/nodes?limit=100&offset=200
```

- `limit`: Results per page (default 500, max 1000)
- `offset`: Number of results to skip
- Response includes `pagination` object with `total`, `limit`, `offset`

For large datasets, consider cursor-based pagination (future enhancement).

---

## CORS Policy

```
Allowed Origins: https://fde-o2c-graph.vercel.app, http://localhost:3000
Allowed Methods: GET, POST, OPTIONS
Allowed Headers: Content-Type, Authorization
Credentials: true (if using cookies)
```

---

## API Versioning

Current version: `v1` (implicit, may be added to paths in future)

Future breaking changes will use `/api/v2/*` paths.

---

## Testing

**cURL Examples**

```bash
# Get all orders
curl "http://localhost:8000/api/graph/nodes?node_type=order&limit=10"

# Get edges for an order
curl "http://localhost:8000/api/graph/edges?source_type=order&source_id=order:ORD-2026-001"

# Get order details
curl "http://localhost:8000/api/node/order:ORD-2026-001/details"

# Send chat query
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Which orders from Acme Corp are pending?", "chat_id": "session-1"}'
```

---

## Implementation Notes

- All `node_id` fields are globally unique within their type (e.g., `SalesOrder:740506`)
- Node types use PascalCase (e.g., `SalesOrder`, `Customer`)
- Edge types use UPPER_SNAKE_CASE (e.g., `CUSTOMER_PLACED_ORDER`)
- Timestamps are ISO-8601 format, UTC timezone
- Monetary amounts are stored as DECIMAL for precision
- Null responses use `null` (not empty strings or 0)
