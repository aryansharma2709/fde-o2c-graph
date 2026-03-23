# Demo Script

## Overview

This script demonstrates the core capabilities of the O2C Explorer in a ~5-10 minute walk-through suitable for a hiring panel or evaluator.

**Goals**: Show graph visualization, query power, LLM grounding, and safety guardrails in action.

---

## Setup (Before Demo)

1. **Start Backend**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```
   Verify: http://localhost:8000/api/health → should see `{"status": "healthy"}`

2. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```
   Visit: http://localhost:5173

3. **Sample Data Loaded**: Verify DuckDB has data
   ```bash
   python -c "import duckdb; print(duckdb.connect('data/sap-orders.duckdb').execute('SELECT COUNT(*) FROM orders').fetchone())"
   # Should output: (some_count,) where count > 0
   ```

---

## Demo Flow (5-10 minutes)

### Section 1: Graph Exploration (2 min)

**Narrative**: "Let me show you the interactive graph of our Order-to-Cash process."

**Actions**:

1. **Load initial graph**
   - Open http://localhost:5173
   - Click "Load Graph" (or auto-loads)
   - **Show**: Canvas renders ~50 nodes (orders, suppliers, fulfillments, invoices)
   - Nodes are color-coded: blue=orders, green=suppliers, orange=invoices, red=payments
   - Edges show relationships: INCLUDES, FULFILLED_BY, INVOICED_IN, PAID_BY

2. **Interactivity**
   - Drag a node → show layout re-flows
   - Hover over node → tooltip shows ID and key attributes (e.g., "Order #ORD-2026-001, Status: completed")
   - Click on a node → right panel shows full details
     - **Example**: Click an order node → shows:
       - Order ID, created date, status, total amount
       - Related items (count)
       - Invoices (count, total)
       - Payments (count, amounts)
       - Supplier name & location
     - **Show**: "Here's the full context for this order. All data is queryable."

3. **Filter demonstration**
   - Filter by supplier: Select "Acme Corp" from dropdown
   - **Show**: Graph re-renders showing only orders from this supplier
   - **Narrative**: "The graph updates in real-time based on filters. This is efficient because we project edges on-demand from DuckDB."

---

### Section 2: Trace Query (3 min)

**Narrative**: "Now let me show you the tracing capability. Watch as we follow a single order through its entire lifecycle."

**Actions**:

1. **Submit trace query via chat**
   - Focus on chat input (bottom of screen)
   - Type: `"Trace Order #ORD-2025-123 from creation to payment"`
   - Hit enter

2. **Backend processes**
   - LLM recognizes intent: "Trace a single order"
   - Generates SQL: 
     ```sql
     SELECT o.order_id, o.created_date, i.invoice_date, p.payment_date
     FROM orders o
     LEFT JOIN invoices i ON o.order_id = i.order_id
     LEFT JOIN payments p ON i.invoice_id = p.invoice_id
     WHERE o.order_id = 'ORD-2025-123'
     ```
   - Executes against DuckDB (should be < 50ms)

3. **Response & Grounding**
   - Chat shows: `"Order #ORD-2025-123 was created on Jan 10, 2026. First invoice (INV-001) appeared on Jan 15. Payment (PAY-001) completed on Feb 5. Total O2C cycle: 26 days."`
   - **Show**: Beneath the response, display "Grounding Evidence":
     - Executed SQL (read-only SELECT)
     - Result rows: [1 row]
     - Execution time: 45ms
     - Highlighted nodes in graph: ORD-2025-123, INV-001, PAY-001 (bolded/colored)
   - **Narrative**: "Every answer is grounded in actual query results. You can see the exact SQL executed and the data it found."

---

### Section 3: Ranking Query (2 min)

**Narrative**: "Let's run a more analytical query: ranking orders by their O2C cycle time."

**Actions**:

1. **Submit ranking query**
   - Type: `"Top 5 slowest orders by O2C time this month"`
   - Hit enter

2. **Backend processes**
   - LLM intent: "Analytical ranking query"
   - Generates SQL:
     ```sql
     SELECT o.order_id, DATEDIFF(day, o.created_date, COALESCE(p.payment_date, NOW())) as o2c_days
     FROM orders o
     LEFT JOIN invoices i ON o.order_id = i.order_id
     LEFT JOIN payments p ON i.invoice_id = p.invoice_id
     WHERE MONTH(o.created_date) = MONTH(NOW()) AND YEAR(o.created_date) = YEAR(NOW())
     ORDER BY o2c_days DESC
     LIMIT 5
     ```
   - Executes (< 100ms)

3. **Response & Highlighting**
   - Chat shows: 
     ```
     "Top 5 slowest orders this month:
     1. ORD-2025-501: 42 days
     2. ORD-2025-502: 38 days
     3. ORD-2025-503: 35 days
     4. ORD-2025-504: 31 days
     5. ORD-2025-505: 28 days
     
     Order #501 was delayed by invoicing (invoice 15 days late)."
     ```
   - **Show**: Grounding panel highlights all 5 orders in graph (bolded nodes)
   - **Narrative**: "The system automatically highlighted the relevant orders in the graph. You can click any of them for deep-dive details."

---

### Section 4: Anomaly Detection Query (2 min)

**Narrative**: "One more advanced query: anomaly detection. Let's find duplicate payments."

**Actions**:

1. **Submit anomaly query**
   - Type: `"Show me invoices with duplicate payments in the last 90 days"`
   - Hit enter

2. **Backend processes**
   - LLM generates SQL:
     ```sql
     SELECT i.invoice_id, COUNT(p.payment_id) as payment_count, SUM(p.amount) as total_paid
     FROM invoices i
     JOIN payments p ON i.invoice_id = p.invoice_id
     WHERE i.invoice_date >= CURRENT_DATE - INTERVAL 90 DAY
     GROUP BY i.invoice_id
     HAVING COUNT(p.payment_id) > 1
     ORDER BY payment_count DESC
     ```

3. **Response**
   - Chat shows: 
     ```
     "Found 3 invoices with multiple payments in the last 90 days (possible duplicates):
     - INV-2025-102: 2 payments totaling $50,000 (expected: $25,000 each) ⚠️
     - INV-2025-105: 2 payments totaling $30,000 (expected: $15,000 each) ⚠️
     - INV-2025-110: 3 payments totaling $45,000 (expected: $15,000 each) ⚠️"
     ```
   - **Show**: Graph highlights these invoices and their related payments in red (anomaly color)

---

### Section 5: Guardrail Rejection (1 min)

**Narrative**: "Finally, let me show you the safety guardrails. The system refuses to answer out-of-domain questions."

**Actions**:

1. **Submit out-of-domain query**
   - Type: `"What's the weather in Singapore?"`
   - Hit enter

2. **Backend processes**
   - LLM semantic check: "Singapore weather" is not about orders/suppliers/finance
   - Classifier rejects: confidence < 0.3 for dataset relevance
   - **No SQL generated** (validation prevents it)

3. **Response**
   - Chat shows: 
     ```
     "This system is designed to answer questions related to the provided dataset only."
     ```
   - No grounding evidence (not a valid query)
   - **Narrative**: "The system cleanly rejects off-topic questions. This prevents LLM hallucination and keeps the conversation focused."

4. **Bonus: Ambiguous query**
   - Type: `"What about the thing?"`
   - Response: 
     ```
     "I didn't understand that question. Try asking about:
     • Orders (status, dates, amounts)
     • Suppliers & customers
     • Fulfillments & receipts
     • Invoices & payments"
     ```

---

## Advanced Features (If time permits)

### Query History
- **Show**: Chat panel has "History" tab
- Click to view previous queries and results
- Click "Replay" to re-run a query with same parameters

### Custom Traversal
- Type: `"Show me all materials from Acme Corp's orders"`
- System traverses: Supplier → Order → OrderItem → Material
- Highlights path in graph

### Export Results
- Click "Export" on any query result
- Download as CSV or JSON
- **Narrative**: "You can export query results for further analysis in Excel or other tools."

---

## Talking Points

### 1. **Why DuckDB for O2C?**
   - SAP data is inherently relational → DuckDB is perfect
   - In-process, no deployment overhead → great for assignments
   - Fast analytical queries → instant insights
   - Reproducible → answers are always consistent

### 2. **Graph Projection Benefits**
   - Not a graph database (overkill for relational data)
   - Project edges on-demand → flexible schema
   - Query-time evaluation → always fresh
   - Lower storage footprint → no duplication

### 3. **LLM Integration Done Right**
   - SQL generation from natural language → powerful & intuitive
   - **All answers grounded in query results** → no hallucination
   - Validation layer prevents SQL injection → safe
   - Out-of-domain detection → focused scope

### 4. **Safety & Guardrails**
   - Read-only SQL only (SELECT no INSERT/UPDATE/DELETE)
   - Query timeouts → prevent runaway queries
   - Result limits → no data exfiltration
   - Input sanitization → prevent prompt injection

### 5. **Code Quality**
   - Modular architecture (Services, Queries, Utils)
   - Testable design (dependency injection, pure functions)
   - Type safety (Pydantic schemas, TypeScript)
   - Production-ready (error handling, logging, monitoring)

---

## Troubleshooting During Demo

| Issue | Fix |
|-------|-----|
| Graph not loading | Check backend is running: `curl http://localhost:8000/api/health` |
| Chat query hangs | LLM API timeout. Check API key is valid. |
| CORS error in browser console | Backend CORS config needs frontend URL. Update `app/main.py` |
| Slow query execution | DuckDB query is complex. Show execution time in grounding panel. |
| No sample data | Run `python scripts/load_dataset.py` |

---

## Demo Time Budget

| Section | Duration | Flexible? |
|---------|----------|-----------|
| Graph exploration | 2 min | Yes (skip filters if short on time) |
| Trace query | 3 min | No (core feature) |
| Ranking query | 2 min | Yes (can skip if time-constrained) |
| Anomaly detection | 2 min | Yes (bonus if time allows) |
| Guardrail rejection | 1 min | No (important for safety story) |
| **Total** | **~10 min** | Flexible to 5-7 min |

---

## Q&A Preparation

**Q: Why not use a real graph database like Neo4j?**
A: SAP data is fundamentally relational. DuckDB's SQL is more natural here. Graph databases excel when relationships are first-class (social networks, knowledge graphs). We project edges on-demand for maximum flexibility.

**Q: How do you prevent LLM hallucination?**
A: Every answer is grounded in validated query results. LLM only synthesizes findings from actual data, not generating answers from thin air. If a query fails validation, we reject it instead of attempting a fallback.

**Q: What's the query latency?**
A: Graph queries (nodes/edges): 50-200ms. Chat queries: 500-2000ms (includes LLM inference). We aim for P95 < 2s on production hardware.

**Q: How would this scale to millions of rows?**
A: DuckDB can handle gigabyte-scale data efficiently. For multi-terabyte, we'd partition the data or use a column store like Iceberg. FastAPI is horizontally scalable behind a load balancer.

**Q: Why Render and not AWS/GCP?**
A: Simplicity. Render's free tier is perfect for take-home assignments. For production, we'd use AWS RDS for DuckDB backups and Lambda for async LLM calls.

---

## Post-Demo Actions

1. **Push code**: `git push origin main`
   - Triggers automatic deploy to Vercel (frontend) & Render (backend)
   
2. **Gather feedback**: 
   - Architecture clarity?
   - Code quality?
   - Safety guardrails convincing?
   - Performance acceptable?

3. **Next steps**:
   - Add unit tests (target 80% coverage)
   - Implement bonus features (anomaly detection, custom traversals)
   - Performance profiling & optimization
