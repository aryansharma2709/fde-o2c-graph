# Data Model

## Dataset Audit

**Status**: Pending ⏳

**To Complete During Implementation**
- [ ] Confirm table names and column counts
- [ ] Identify PII columns (supplier names, customer names)
- [ ] Check for NULL handling strategy
- [ ] Verify date formats (are they ISO-8601?)
- [ ] Detect primary/foreign key structure
- [ ] Sample row count per table
- [ ] Identify outliers / data quality issues

**Expected Structure** (to be validated)
```
Tables: Orders, OrderItems, Fulfillments, Invoices, Payments,
        Suppliers, Materials, Plants, Customers
Estimated rows: 100K - 1M
Estimated size: 50-500 MB
```

---

## Node Types

### Core Entities

| Node Type | Purpose | Unique ID | Key Attributes |
|-----------|---------|-----------|-----------------|
| `order` | Purchase/sales order header | `order_id` | `created_date`, `status`, `total_amount`, `customer_id`, `supplier_id` |
| `order_item` | Line item in an order | `item_id` | `order_id`, `material_id`, `quantity`, `unit_price` |
| `fulfillment` | Goods receipt / shipment | `fulfillment_id` | `item_id`, `received_qty`, `received_date`, `warehouse_id` |
| `receipt` | Warehouse receipt event | `receipt_id` | `fulfillment_id`, `received_date`, `warehouse_location` |
| `invoice` | Billing document | `invoice_id` | `order_id`, `amount`, `invoice_date`, `due_date` |
| `payment` | Payment transaction | `payment_id` | `invoice_id`, `amount`, `payment_date`, `method` |
| `supplier` | Vendor / procurement partner | `supplier_id` | `name`, `location`, `country`, `rating` |
| `customer` | Buyer / end customer | `customer_id` | `name`, `location`, `country` |
| `material` | Product / SKU | `material_id` | `description`, `category`, `unit_of_measure`, `price` |
| `plant` | Manufacturing / distribution site | `plant_id` | `name`, `location`, `capacity` |

---

## Edge Types (Relationships)

### Process Flow Edges

| Edge Type | Source | Target | Meaning | Volume Est. |
|-----------|--------|--------|---------|-------------|
| `INCLUDES` | `order` | `order_item` | Order contains line items | ~1.5M (avg 3-5 lines/order) |
| `FULFILLED_BY` | `order_item` | `fulfillment` | Item fulfilled by shipment | ~1.5M (1:1 typically) |
| `RECEIVED_IN` | `fulfillment` | `receipt` | Fulfillment creates receipt | ~1.5M (1:1) |
| `INVOICED_IN` | `order_item` | `invoice` | Item billed in invoice | ~1.5M (batched, 3-10 per invoice) |
| `PAID_BY` | `invoice` | `payment` | Invoice payment | ~300K (avg 5 invoices/payment?) |

### Master Data Edges

| Edge Type | Source | Target | Meaning | Volume Est. |
|-----------|--------|--------|---------|-------------|
| `SUPPLIED_BY` | `order` | `supplier` | Order sourced from supplier | ~300K (distinct supplier relationships) |
| `ORDERED_BY` | `order` | `customer` | Order placed by customer | ~100K (distinct customer relationships) |
| `USES_MATERIAL` | `order_item` | `material` | Line item references material | ~1.5M (many items, fewer materials) |
| `PRODUCED_AT` | `material` | `plant` | Material produced at plant | ~10K (material-plant mapping) |
| `SOURCES_FROM` | `supplier` | `material` | Supplier provides material | ~50K (supplier-material catalog) |

---

## Join Paths

**To be validated during dataset exploration**

### Standard O2C Trace
```
Order → OrderItem → Fulfillment → Receipt
       ↓
       → Invoice → Payment
```

### Supplier Analysis
```
Supplier → Order → OrderItem → Material
```

### Material Flow
```
Material → OrderItem → Order
                    ↓
                    → Fulfillment
```

### Cash Reconciliation
```
Order → OrderItem → Invoice → Payment
                              ↓
                              (trace to bank)
```

---

## Query Coverage Map

**To be populated as implementation progresses**

### Query Category: Order Status

| Question | Table Joins | Estimated Rows | Complexity |
|----------|-------------|-----------------|-----------|
| "Show all orders from Supplier X" | Order JOIN Supplier | 100-10K | Low |
| "Which orders haven't been invoiced?" | Order LEFT JOIN Invoice | 1K-10K | Low |
| "Timeline of Order #123" | Order + Items + Fulfillment + Invoice + Payment | 1-20 | Medium |

### Query Category: Fulfillment Analysis

| Question | Table Joins | Estimated Rows | Complexity |
|----------|-------------|-----------------|-----------|
| "Orders with late deliveries" | Order JOIN Fulfillment (date diff) | 1K-50K | Medium |
| "Fulfillment gap detection" | Order JOIN OrderItem LEFT JOIN Fulfillment | 1K-20K | Medium |

### Query Category: Payment Anomalies

| Question | Table Joins | Estimated Rows | Complexity |
|----------|-------------|-----------------|-----------|
| "Invoices pending payment > 60 days" | Invoice LEFT JOIN Payment (date range) | 10-1K | Low |
| "Duplicate payment detection" | Payment GROUP BY invoice_id (count > 1) | 1-100 | Low |

### Query Category: Financial Rollups

| Question | Table Joins | Estimated Rows | Complexity |
|----------|-------------|-----------------|-----------|
| "Total spend by supplier" | Order JOIN Supplier, SUM(amount) | 100-10K | Medium |
| "Average order-to-payment cycle" | Order JOIN Payment (date math) | 1K-100K | High |

---

## Schema Transformation (DuckDB DDL)

**To be finalized after dataset audit**

```sql
-- Placeholder structure (to be adapted to actual dataset)

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR,
    order_date DATE,
    status VARCHAR,
    total_amount DECIMAL(15,2),
    customer_id VARCHAR,
    supplier_id VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (order_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id VARCHAR,
    order_id VARCHAR,
    material_id VARCHAR,
    quantity DECIMAL(15,2),
    unit_price DECIMAL(15,2),
    line_total DECIMAL(15,2),
    PRIMARY KEY (item_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS fulfillments (
    fulfillment_id VARCHAR,
    item_id VARCHAR,
    received_qty DECIMAL(15,2),
    received_date DATE,
    warehouse_id VARCHAR,
    PRIMARY KEY (fulfillment_id),
    FOREIGN KEY (item_id) REFERENCES order_items(item_id)
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id VARCHAR,
    order_id VARCHAR,
    amount DECIMAL(15,2),
    invoice_date DATE,
    due_date DATE,
    PRIMARY KEY (invoice_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR,
    invoice_id VARCHAR,
    amount DECIMAL(15,2),
    payment_date DATE,
    method VARCHAR,
    PRIMARY KEY (payment_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id VARCHAR,
    name VARCHAR,
    location VARCHAR,
    country VARCHAR,
    rating DECIMAL(3,1),
    PRIMARY KEY (supplier_id)
);

CREATE TABLE IF NOT EXISTS materials (
    material_id VARCHAR,
    description VARCHAR,
    category VARCHAR,
    unit_of_measure VARCHAR,
    PRIMARY KEY (material_id)
);

-- Indices for common queries
CREATE INDEX idx_order_supplier ON orders(supplier_id);
CREATE INDEX idx_order_customer ON orders(customer_id);
CREATE INDEX idx_order_date ON orders(order_date);
CREATE INDEX idx_order_item_order ON order_items(order_id);
CREATE INDEX idx_order_item_material ON order_items(material_id);
CREATE INDEX idx_fulfillment_item ON fulfillments(item_id);
CREATE INDEX idx_invoice_order ON invoices(order_id);
CREATE INDEX idx_payment_invoice ON payments(invoice_id);
```

---

## Data Quality Considerations

**Potential Issues to Investigate**

- [ ] Missing order status transitions (incomplete O2C trail)
- [ ] Duplicate invoice/payment IDs
- [ ] Orphaned records (invoice without order, payment without invoice)
- [ ] Negative quantities or amounts
- [ ] Date inconsistencies (payment_date before invoice_date)
- [ ] Text encoding issues in supplier/customer names
- [ ] NULL handling in optional fields (PO number, payment method)

**Data Validation Rules**

```python
# Pseudocode for validation layer
class DataValidator:
    def validate_order(self, row):
        assert row.order_date <= row.invoice_date, "Invoice before order"
        assert row.total_amount > 0, "Non-positive order amount"
        return True
    
    def validate_payment(self, row):
        assert row.payment_date >= row.invoice_date, "Payment before invoice"
        assert row.amount > 0, "Non-positive payment"
        return True
```

---

## Materialized Views (Optional Performance)

If query latency becomes an issue:

```sql
-- Daily order summary (materialized)
CREATE TABLE order_daily_summary AS
SELECT 
    DATE(order_date) as day,
    supplier_id,
    COUNT(*) as order_count,
    SUM(total_amount) as daily_spend
FROM orders
GROUP BY DATE(order_date), supplier_id;

-- O2C cycle time metrics
CREATE TABLE o2c_metrics AS
SELECT 
    o.order_id,
    MIN(i.invoice_date) - o.order_date as days_to_invoice,
    MIN(p.payment_date) - MIN(i.invoice_date) as days_to_payment,
    MIN(p.payment_date) - o.order_date as total_o2c_days
FROM orders o
LEFT JOIN invoices i ON o.order_id = i.order_id
LEFT JOIN payments p ON i.invoice_id = p.invoice_id
GROUP BY o.order_id;
```

---

## Next Steps

1. Unzip `data/raw/sap-order-to-cash-dataset.zip`
2. Explore actual table structure with exploratory SQL
3. Validate node/edge types against real data
4. Finalize schema DDL and indices
5. Build sample graph projections
6. Create integration tests with real data
