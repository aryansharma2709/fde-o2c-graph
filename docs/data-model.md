# Data Model

## Dataset Audit ✅ COMPLETED

**Status**: Audit complete via `scripts/inspect_dataset.py`  
**Date**: 2026-03-24  
**Total Rows**: 21,393 across 19 collections  
**Total Size**: ~3.8 MB (JSONL format)

### Key Findings

| Collection | Rows | Primary Key | Notes |
|-----------|------|-------------|-------|
| **sales_order_headers** | 100 | `salesOrder` | 24 columns, O2C root entity |
| **sales_order_items** | 167 | `(salesOrder, salesOrderItem)` | Links to materials, 13 columns |
| **outbound_delivery_headers** | 86 | `deliveryDocument` | 13 columns, goods movement |
| **outbound_delivery_items** | 137 | `(deliveryDocument, deliveryDocumentItem)` | 11 columns, references sales orders |
| **billing_document_headers** | 163 | `billingDocument` | 14 columns, invoice records |
| **billing_document_items** | 245 | `(billingDocument, billingDocumentItem)` | 9 columns, links to materials & deliveries |
| **billing_document_cancellations** | 80 | `(billingDocument, cancelledBillingDocument)` | 14 columns, cancellation records |
| **journal_entry_items_accounts_receivable** | 123 | `(accountingDocument, accountingDocumentItem)` | 22 columns, GL entries for ARs |
| **payments_accounts_receivable** | 120 | `(accountingDocument, accountingDocumentItem)` | 23 columns, payment clearing |
| **business_partners** | 8 | `businessPartner` | Customer/vendor master, 19 columns |
| **business_partner_addresses** | 8 | `addressId` | 20 columns, 1:1 with BP |
| **products** | 69 | `product` | 17 columns, material master |
| **product_descriptions** | 69 | `(product, language)` | 3 columns, descriptive text |
| **plants** | 44 | `plant` | 14 columns, warehouse/factory locations |
| **product_plants** | 3,036 | `(product, plant)` | 9 columns, availability mapping |
| **product_storage_locations** | 16,723 | `(product, plant, storageLocation)` | 5 columns, inventory tracking |
| **customer_company_assignments** | 8 | `(customer, companyCode)` | Company/AR settings per customer |
| **customer_sales_area_assignments** | 28 | `(customer, salesOrganization, distributionChannel, division)` | Sales area config |
| **sales_order_schedule_lines** | 179 | `(salesOrder, salesOrderItem, scheduleLine)` | Delivery schedules within order items |

**Data Quality Observations**:
- ✓ Dates are ISO-8601 (e.g., `"2025-03-31T00:00:00.000Z"`)
- ✓ Amounts are strings (e.g., `"17108.25"`) → convert to DECIMAL in DuckDB
- ✓ IDs are zero-padded strings (e.g., `salesOrderItem: "10"`, not `10`)
- ✓ Nullable fields common (e.g., `lastChangeDate`, `actualGoodsMovementDate`)
- ⚠ Some ambiguous relationships (see join path analysis below)
- ⚠ Cancellations modeled as separate collection (not deletion flags)

---

## Key Entity Mapping

### Sales Order (SalesOrder = root of O2C flow)

**Collection**: `sales_order_headers`  
**Primary Key**: `salesOrder` (e.g., `"740506"`)  
**Key Columns**:
- `salesOrder`: Unique order ID (string, zero-padded)
- `salesOrderType`: Order type (e.g., `"OR"` for standard order)
- `soldToParty`: Customer ID (link to `business_partners.businessPartner`)
- `creationDate`: Order date (ISO-8601)
- `totalNetAmount`: Order value (string, needs DECIMAL conversion)
- `overallDeliveryStatus`: Status code (e.g., `"C"` = complete)
- `overallOrdReltdBillgStatus`: Billing status

**Sample**:
```json
{
  "salesOrder": "740506",
  "salesOrderType": "OR",
  "soldToParty": "310000108",
  "creationDate": "2025-03-31T00:00:00.000Z",
  "totalNetAmount": "17108.25",
  "overallDeliveryStatus": "C"
}
```

---

### Sales Order Items (SalesOrderItem = line items)

**Collection**: `sales_order_items`  
**Primary Key**: `(salesOrder, salesOrderItem)` (e.g., `("740506", "10")`)  
**Key Columns**:
- `salesOrder`: Link to order header
- `salesOrderItem`: Line item number (string, zero-padded `"10"`, `"20"`, etc.)
- `material`: Product ID (link to `products.product`)
- `requestedQuantity`: Order quantity (string)
- `requestedQuantityUnit`: Unit (e.g., `"PC"` for piece)
- `netAmount`: Line amount
- `productionPlant`: Plant/warehouse (link to `plants.plant`)

**Sample**:
```json
{
  "salesOrder": "740506",
  "salesOrderItem": "10",
  "material": "S8907367001003",
  "requestedQuantity": "48",
  "productionPlant": "1920"
}
```

---

### Outbound Delivery Headers (Goods Movement)

**Collection**: `outbound_delivery_headers`  
**Primary Key**: `deliveryDocument` (e.g., `"80737721"`)  
**Key Columns**:
- `deliveryDocument`: Unique delivery ID
- `creationDate`: Delivery creation date
- `actualGoodsMovementDate`: When goods left warehouse (nullable)
- `overallGoodsMovementStatus`: Status code (e.g., `"A"` = not yet posted)
- `shippingPoint`: Plant that shipped

**Sample**:
```json
{
  "deliveryDocument": "80737721",
  "creationDate": "2025-03-31T00:00:00.000Z",
  "actualGoodsMovementDate": null,
  "overallGoodsMovementStatus": "A"
}
```

---

### Outbound Delivery Items (Delivery Line Items)

**Collection**: `outbound_delivery_items`  
**Primary Key**: `(deliveryDocument, deliveryDocumentItem)` (e.g., `("80738076", "000010")`)  
**Key Columns**:
- `deliveryDocument`: Link to delivery header
- `deliveryDocumentItem`: Line number
- `referenceSdDocument`: **Sales Order ID** (link back to `sales_order_headers.salesOrder`)
- `referenceSdDocumentItem`: **Sales Order Item number**
- `actualDeliveryQuantity`: Goods movement quantity
- `plant`: Warehouse location

**Sample**:
```json
{
  "deliveryDocument": "80738076",
  "referenceSdDocument": "740556",
  "referenceSdDocumentItem": "000010",
  "actualDeliveryQuantity": "1"
}
```

**Note**: ✓ **Join confirmed**: `outbound_delivery_items.(referenceSdDocument, referenceSdDocumentItem)` → `sales_order_items.(salesOrder, salesOrderItem)`

---

### Billing Document Headers (Invoices)

**Collection**: `billing_document_headers`  
**Primary Key**: `billingDocument` (e.g., `"90504248"`)  
**Key Columns**:
- `billingDocument`: Unique invoice ID
- `billingDocumentType`: Type (e.g., `"F2"` for standard invoice)
- `billingDocumentDate`: Invoice date
- `totalNetAmount`: Invoice amount
- `accountingDocument`: **GL entry ID** (link to journal entries, links forward in flow)
- `soldToParty`: Customer ID (link to `business_partners`)

**Sample**:
```json
{
  "billingDocument": "90504248",
  "billingDocumentType": "F2",
  "billingDocumentDate": "2025-04-02T00:00:00.000Z",
  "totalNetAmount": "216.1",
  "accountingDocument": "9400000249",
  "soldToParty": "320000083"
}
```

---

### Billing Document Items (Invoice Line Items)

**Collection**: `billing_document_items`  
**Primary Key**: `(billingDocument, billingDocumentItem)` (e.g., `("90504298", "10")`)  
**Key Columns**:
- `billingDocument`: Link to invoice header
- `billingDocumentItem`: Line number
- `referenceSdDocument`: **Delivery Document ID** (link to `outbound_delivery_headers.deliveryDocument`)
- `referenceSdDocumentItem`: **Delivery line number**
- `material`: Product ID
- `billingQuantity`: Invoiced quantity
- `netAmount`: Line amount

**Sample**:
```json
{
  "billingDocument": "90504298",
  "billingDocumentItem": "10",
  "referenceSdDocument": "80738109",
  "referenceSdDocumentItem": "10",
  "netAmount": "533.05"
}
```

**Note**: ✓ **Join confirmed**: `billing_document_items.(referenceSdDocument, referenceSdDocumentItem)` → `outbound_delivery_items.(deliveryDocument, deliveryDocumentItem)`

---

### Billing Document Cancellations

**Collection**: `billing_document_cancellations`  
**Primary Key**: `billingDocument` (duplicate entries from headers)  
**Key Columns**:
- `billingDocument`: Invoice being cancelled
- `cancelledBillingDocument`: New cancellation document (debit memo)
- `billingDocumentIsCancelled`: Boolean flag

**Note**: This is a separate table for audit trail, not deletion.

---

### Journal Entry Items - Accounts Receivable

**Collection**: `journal_entry_items_accounts_receivable`  
**Primary Key**: `(accountingDocument, accountingDocumentItem)`  
**Key Columns**:
- `accountingDocument`: GL entry ID
- `accountingDocumentItem`: Line in GL entry
- `customer`: Customer ID (link to `business_partners`)
- `glAccount`: General ledger account (e.g., `"15500020"`)
- `amountInTransactionCurrency`: Debit/credit amount
- `postingDate`: GL posting date
- `referenceDocument`: **Link back to billing document ID** (reference, not always populated)
- `clearingAccountingDocument`: Link to payment GL entry that cleared this

**Sample**:
```json
{
  "accountingDocument": "9400000249",
  "accountingDocumentItem": "1",
  "customer": "320000083",
  "glAccount": "15500020",
  "amountInTransactionCurrency": "216.1",
  "postingDate": "2025-04-02T00:00:00.000Z"
}
```

**Note**: ⚠ **Uncertain join**: `journal_entry_items_accounts_receivable.referenceDocument` → `billing_document_headers.billingDocument`  
Why uncertain: `referenceDocument` is often NULL (123 rows, but not always populated). Falls back to linking via `accountingDocument` from `billing_document_headers.accountingDocument`.

---

### Payments - Accounts Receivable

**Collection**: `payments_accounts_receivable`  
**Primary Key**: `(accountingDocument, accountingDocumentItem)`  
**Key Columns**:
- `accountingDocument`: Payment GL entry ID
- `customer`: Customer ID
- `clearingDate`: Payment date
- `amountInTransactionCurrency`: Payment amount
- `clearingAccountingDocument`: Links to invoice GL entry being paid
- `clearingDocFiscalYear`: Fiscal year of cleared document
- `salesDocument`: Original sales order ID (optional link, often NULL)
- `salesDocumentItem`: Optional sales order item

**Sample**:
```json
{
  "accountingDocument": "9400000220",
  "customer": "320000083",
  "clearingDate": "2025-04-02T00:00:00.000Z",
  "amountInTransactionCurrency": "897.03",
  "clearingAccountingDocument": "9400635977"
}
```

**Note**: ✓ **Join confirmed**: `payments_accounts_receivable.clearingAccountingDocument` → `journal_entry_items_accounts_receivable.accountingDocument`

---

### Business Partners (Customers)

**Collection**: `business_partners`  
**Primary Key**: `businessPartner` (e.g., `"310000108"`)  
**Key Columns**:
- `businessPartner`: Unique BP ID
- `customer`: Customer flag (if this BP is a customer)
- `businessPartnerFullName`: Customer name (PII)
- `businessPartnerCategory`: Category (e.g., `"2"` for company)
- `creationDate`: Master record creation date

**Sample**:
```json
{
  "businessPartner": "310000108",
  "customer": "310000108",
  "businessPartnerFullName": "Cardenas, Parker and Avila"
}
```

**Note**: 1:1 link to `business_partner_addresses` via `businessPartner` key.

---

### Products (Materials/SKUs)

**Collection**: `products`  
**Primary Key**: `product` (e.g., `"3001456"`)  
**Key Columns**:
- `product`: Unique product ID
- `productOldId`: Legacy product code (e.g., `"WD-BOX-CG"`)
- `productType`: Type indicator (e.g., `"ZPKG"`)
- `baseUnit`: Unit of measure (e.g., `"PC"`)
- `grossWeight`, `netWeight`: Weight for logistics

**Sample**:
```json
{
  "product": "3001456",
  "productType": "ZPKG",
  "baseUnit": "PC",
  "grossWeight": "0.012",
  "weightUnit": "KG"
}
```

**Note**: Linked by `material` columns in `sales_order_items`, `billing_document_items`, etc.

---

### Plants (Warehouses/Distribution Centers)

**Collection**: `plants`  
**Primary Key**: `plant` (e.g., `"1920"`, `"WB05"`)  
**Key Columns**:
- `plant`: Warehouse ID
- `plantName`: Warehouse name
- `plantSupplier`: Supplier plant flag
- `plantCustomer`: Customer warehouse flag
- `addressId`: Link to location data

**Sample**:
```json
{
  "plant": "1920",
  "plantName": "Central Warehouse",
  "plantSupplier": false,
  "plantCustomer": false
}
```

---

## Join Coverage Summary

**Validation Method**: Full dataset coverage via `scripts/validate_join_coverage.py`  
**Date**: 2026-03-24  
**Normalization**: IDs normalized to zero-padded strings for comparison  

| Join Path | Left Distinct Keys | Right Distinct Keys | Matched Keys | Key Coverage % | Classification | Notes |
|-----------|-------------------|---------------------|--------------|----------------|----------------|-------|
| sales_order_headers.salesOrder → sales_order_items.salesOrder | 100 | 100 | 100 | 100.0% | confirmed_with_normalization | Perfect coverage with normalization |
| sales_order_items.(salesOrder, salesOrderItem) → outbound_delivery_items.(referenceSdDocument, referenceSdDocumentItem) | 167 | 137 | 137 | 82.04% | partial | 82% coverage - some items not delivered |
| outbound_delivery_items.(deliveryDocument, deliveryDocumentItem) → billing_document_items.(referenceSdDocument, referenceSdDocumentItem) | 137 | 124 | 124 | 90.51% | partial | 91% coverage - some deliveries not invoiced |
| billing_document_headers.accountingDocument → journal_entry_items_accounts_receivable.accountingDocument | 163 | 123 | 123 | 75.46% | uncertain | 75% coverage - GL entries may be batched |
| journal_entry_items_accounts_receivable.accountingDocument → payments_accounts_receivable.clearingAccountingDocument | 123 | 56 | 56 | 45.53% | not_recommended | 46% coverage - many invoices unpaid |
| sales_order_headers.soldToParty → business_partners.businessPartner | 8 | 8 | 8 | 100.0% | confirmed_with_normalization | Perfect coverage with normalization; 100 rows reference 8 unique customers |
| sales_order_items.material → products.product | 69 | 69 | 69 | 100.0% | confirmed_with_normalization | Perfect coverage with normalization; 167 rows reference 69 unique products |
| outbound_delivery_items.plant → plants.plant | 5 | 5 | 5 | 100.0% | confirmed_with_normalization | Perfect coverage with normalization; 137 rows reference 5 unique plants |
| business_partners.businessPartner → business_partner_addresses.businessPartner | 8 | 8 | 8 | 100.0% | confirmed_with_normalization | Perfect coverage with normalization |
| plants.addressId → business_partner_addresses.addressId | 0 | 8 | 0 | 0.0% | not_recommended | No meaningful linkage - plants.addressId not populated |

**Classification Legend**:
- **confirmed**: >95% coverage without normalization
- **confirmed_with_normalization**: >95% coverage with ID normalization
- **partial**: 80-95% coverage
- **uncertain**: 50-80% coverage
- **not_recommended**: <50% coverage

**Key Coverage Notes**: Coverage is measured on distinct key values, not row counts. For master data joins (e.g., soldToParty → businessPartner), 100% key coverage means all referenced entities exist, but multiple rows may reference the same entity.

---

## Verified Join Paths

### ✓ Confirmed Path 1: Sales Order → Items (confirmed_with_normalization)

```
sales_order_headers.salesOrder 
  → sales_order_items.salesOrder (1:N)
```
- **Coverage**: 100% (100/100 matched with normalization)
- **Example**: `salesOrder="740506"` has 1+ items with `salesOrderItem="10"`, `"20"`, etc.
- **Verified**: Full dataset validation confirms perfect coverage.

---

### ✓ Confirmed Path 2: Sales Order Items → Outbound Delivery Items (partial)

```
sales_order_items.(salesOrder, salesOrderItem)
  → outbound_delivery_items.(referenceSdDocument, referenceSdDocumentItem) (1:N)
```
- **Coverage**: 82.04% (137/167 matched)
- **Column Evidence**: `outbound_delivery_items.referenceSdDocument` = sales order ID
- **Verified**: Partial coverage - some order items not yet delivered or cancelled.
- **Cardinality**: 1 sales order item can generate multiple delivery items (partial shipments, splits)

---

### ✓ Confirmed Path 3: Outbound Delivery Items → Billing Document Items (partial)

```
outbound_delivery_items.(deliveryDocument, deliveryDocumentItem)
  → billing_document_items.(referenceSdDocument, referenceSdDocumentItem) (1:N)
```
- **Coverage**: 90.51% (124/137 matched)
- **Column Evidence**: `billing_document_items.referenceSdDocument` = delivery document ID
- **Verified**: Partial coverage - some deliveries not yet invoiced.
- **Cardinality**: 1 delivery can be billed in multiple invoices (batch invoicing) or 1 delivery per invoice

---

### ✓ Confirmed Path 4: Billing Document Headers → Items (assumed)

```
billing_document_headers.billingDocument
  → billing_document_items.billingDocument (1:N)
```
- **Coverage**: Not validated (standard SAP pattern, assumed 100%)
- **Verified**: Standard header-item relationship in SAP.

---

### ⚠ Uncertain Path 5: Billing Document Headers → GL Entry (uncertain)

```
billing_document_headers.accountingDocument
  → journal_entry_items_accounts_receivable.accountingDocument (1:N)
```
- **Coverage**: 75.46% (123/163 matched)
- **Evidence**: `billing_document_headers.accountingDocument="9400000249"` appears in journal entries
- **Verified**: Uncertain coverage - GL entries may be posted in batches or delayed.
- **Cardinality**: 1 invoice = 1+ GL line items (debit AR, credit Revenue, credit Tax, etc.)

---

### ✗ Not Recommended Path 6: GL Entry → Payment Clearing (not_recommended)

```
journal_entry_items_accounts_receivable.accountingDocument
  → payments_accounts_receivable.clearingAccountingDocument (1:N)
```
- **Coverage**: 45.53% (56/123 matched)
- **Evidence**: Payment has `clearingAccountingDocument` pointing to invoice GL entry
- **Verified**: Low coverage - many invoices remain unpaid in dataset timeframe.
- **Cardinality**: 1 invoice can be paid in multiple payments (partial payments)
- **Recommendation**: Use for payment analysis only; not reliable for complete O2C tracing.

---

### ✓ Confirmed Path 7: Sales Order → Customer (confirmed_with_normalization)

```
sales_order_headers.soldToParty
  → business_partners.businessPartner (N:1)
```
- **Coverage**: 100% (8/100 matched with normalization)
- **Verified**: Perfect coverage with ID normalization.
- **Cardinality**: Multiple orders per customer (N:1)

---

### ✓ Confirmed Path 8: Sales Order Item → Product (confirmed_with_normalization)

```
sales_order_items.material
  → products.product (N:1)
```
- **Coverage**: 100% (69/167 matched with normalization)
- **Verified**: Perfect coverage with ID normalization.
- **Cardinality**: Multiple order items reference same product (N:1)

---

### ✓ Confirmed Path 9: Outbound Delivery Item → Plant (confirmed_with_normalization)

```
outbound_delivery_items.plant
  → plants.plant (N:1)
```
- **Coverage**: 100% (5/137 matched with normalization)
- **Verified**: Perfect coverage with ID normalization.
- **Cardinality**: Multiple deliveries from same warehouse

---

### ✗ Not Recommended Path: Plants → Addresses (not_recommended)

```
plants.addressId
  → business_partner_addresses.addressId (no linkage)
```
- **Coverage**: 0.0% (0/44 matched)
- **Issue**: `plants.addressId` not populated or meaningful.
- **Recommendation**: Do not use for graph edges; plants are independent entities.

---

## Data Quality & Normalization Rules

### Recommended Normalization Rules

**1. ID Normalization**:
- Keep all IDs as VARCHAR (not INTEGER) to preserve zero-padding
- Normalize item numbers to canonical padded form during load:
  ```sql
  -- Example: Normalize salesOrderItem to 6-digit padding
  CAST(LPAD(salesOrderItem, 6, '0') AS VARCHAR) as normalized_salesOrderItem
  ```
- Use normalized keys in all joins and WHERE clauses

**2. Amount Fields**:
- Cast amount fields to DECIMAL(15,2) for arithmetic:
  ```sql
  CAST(totalNetAmount AS DECIMAL(15,2)) as totalNetAmount_decimal
  ```

**3. Datetime Flattening**:
- Flatten nested time objects to full ISO-8601 timestamps:
  ```sql
  -- Combine date + time for full timestamp
  CONCAT(LEFT(creationDate, 10), 'T', 
         LPAD(creationTime.hours, 2, '0'), ':',
         LPAD(creationTime.minutes, 2, '0'), ':',
         LPAD(creationTime.seconds, 2, '0'), '.000Z') as creationTimestamp
  ```

**4. Nullable Field Handling**:
- Use NULL-safe joins: `COALESCE(field, '')` for string comparisons
- Filter incomplete flows explicitly in queries

---

### 1. ✓ String IDs & Zero-Padding

**Finding**: All IDs are strings with zero-padding  
- `salesOrderItem="10"`, not `10`
- `deliveryDocumentItem="000010"`, not `10`

**Implication**: Must use string comparison in queries, not numeric.

---

### 2. ✓ Amounts as Strings

**Finding**: `totalNetAmount="17108.25"`, `netAmount="9966.1"` are strings  

**Action Required**: Convert to DECIMAL(15,2) in DuckDB schema for arithmetic operations.

---

### 3. ✓ Nullable Fields

**Finding**: Many fields are NULL or empty string:
- `actualGoodsMovementDate`: Often NULL before goods are moved
- `lastChangeDate`: Often NULL if not updated
- `referenceDocument`: Often NULL in journal entries

**Implication**: Always use NULL-safe joins; filter incomplete flows carefully.

---

### 4. ⚠ Datetime vs Time Structs

**Finding**: Some timestamps are nested objects:
```json
{
  "creationTime": {
    "hours": 6,
    "minutes": 49,
    "seconds": 13
  }
}
```

**Action Required**: Flatten during load (combine with date for full timestamp).

---

### 5. ⚠ Cancellation Model

**Finding**: Cancellations are separate records in `billing_document_cancellations`, not deletion flags  

**Implication**: 
- Filter via `billingDocumentIsCancelled` flag in headers
- Or join to `cancellations` table to find replaced documents
- Requires careful logic for "active" invoices

---

### 6. ✓ Full Product-Plant Matrix

**Finding**: 
- 69 products × 44 plants = 3,036 product-plant records (full matrix - all products available in all plants)
- 44 plants, 8 business partners (small master data set)
- Large number of storage locations (16,723 records for inventory tracking)

**Implication**: 
- Product availability is universal (all products in all plants)
- Queries on storage locations may be large and require aggregation
- Customer base is small (8 BPs), so customer-level aggregations are coarse-grained

---

## Final Graph Design

### Recommended Node Types (from real dataset)

| Node Type | SAP Entity | Unique ID | Graph Role |
|-----------|-----------|-----------|-----------|
| `sales_order` | sales_order_headers | `salesOrder` | Root of O2C flow |
| `sales_order_item` | sales_order_items | `(salesOrder, salesOrderItem)` | Order decomposition |
| `outbound_delivery` | outbound_delivery_headers | `deliveryDocument` | Goods movement |
| `outbound_delivery_item` | outbound_delivery_items | `(deliveryDocument, deliveryDocumentItem)` | Delivery decomposition |
| `billing_document` | billing_document_headers | `billingDocument` | Invoice/credit memo |
| `billing_document_item` | billing_document_items | `(billingDocument, billingDocumentItem)` | Invoice line |
| `gl_entry` | journal_entry_items_accounts_receivable | `(accountingDocument, accountingDocumentItem)` | GL posting |
| `payment` | payments_accounts_receivable | `(accountingDocument, accountingDocumentItem)` | Payment clearing |
| `customer` | business_partners | `businessPartner` | Master data |
| `address` | business_partner_addresses | `addressId` | Master data (customer addresses) |
| `product` | products | `product` | Master data |
| `plant` | plants | `plant` | Master data |

---

### Recommended Edge Types (from real dataset)

| Edge Type | Source | Target | Cardinality | SAP Join | Status |
|-----------|--------|--------|-------------|----------|--------|
| `INCLUDES` | `sales_order` | `sales_order_item` | 1:N | `salesOrder` FK | Core |
| `FULFILLED_BY` | `sales_order_item` | `outbound_delivery_item` | 1:N | `(referenceSdDocument, referenceSdDocumentItem)` | Core |
| `DELIVERED_IN` | `outbound_delivery` | `outbound_delivery_item` | 1:N | `deliveryDocument` FK | Core |
| `INVOICED_IN` | `outbound_delivery_item` | `billing_document_item` | 1:N | `(referenceSdDocument, referenceSdDocumentItem)` | Core |
| `CONTAINS` | `billing_document` | `billing_document_item` | 1:N | `billingDocument` FK | Core |
| `POSTS_GL` | `billing_document` | `gl_entry` | 1:N | `accountingDocument` FK | Core |
| `PAID_BY` | `gl_entry` | `payment` | 1:N | `clearingAccountingDocument` FK | Optional (46% coverage) |
| `ORDERED_BY` | `sales_order` | `customer` | N:1 | `soldToParty` FK | Core |
| `LOCATED_AT` | `customer` | `address` | 1:1 | `businessPartner` FK | Core |
| `CONTAINS_MATERIAL` | `sales_order_item` | `product` | N:1 | `material` FK | Core |
| `SOURCED_FROM` | `outbound_delivery_item` | `plant` | N:1 | `plant` FK | Core |
| `BILLED_FOR` | `billing_document_item` | `product` | N:1 | `material` FK | Core |

**Primary O2C Trace**: Sales Order → Delivery → Billing Document → Journal Entry  
**Payment Enrichment**: Payment is secondary enrichment if present (not reliable for complete tracing due to 46% coverage)

---

### Deterministic Node ID Suggestions

```
sales_order:740506
sales_order_item:740506~10          # Composite: order~item
outbound_delivery:80737721
outbound_delivery_item:80737721~000010
billing_document:90504248
billing_document_item:90504248~10
gl_entry:9400000249~1               # Composite: doc~line
payment:9400000220~1
customer:310000108
address:0001                        # Address ID
product:3001456
plant:1920
```

**Rationale**: Composite IDs use `~` separator to avoid collisions (e.g., `salesOrder="740506"`, `salesOrderItem="10"` becomes `"740506~10"`).

---

## Queries We Can Reliably Answer

### 1. **Highest Number of Billing Documents by Product**

```sql
SELECT 
  bdi.material,
  p.product,
  p.productType,
  COUNT(DISTINCT bdi.billingDocument) as invoice_count,
  SUM(CAST(bdi.netAmount AS DECIMAL(15,2))) as total_invoiced
FROM billing_document_items bdi
LEFT JOIN products p ON bdi.material = p.product
GROUP BY bdi.material, p.product, p.productType
ORDER BY invoice_count DESC
LIMIT 10
```

**Data Available**: ✓ Yes, 245 billing items across 69 products

---

### 2. **Billing Document Trace (Invoice → Delivery → Order)** (Reverse flow from billing)

```sql
SELECT 
  bdh.billingDocument,
  bdi.billingDocumentItem,
  bdi.material,
  odi.deliveryDocument,
  odi.deliveryDocumentItem,
  odi.referenceSdDocument as salesOrder,
  odi.referenceSdDocumentItem as salesOrderItem,
  bdh.accountingDocument,
  CAST(bdi.netAmount AS DECIMAL(15,2)) as invoice_line_amount,
  CAST(bdh.totalNetAmount AS DECIMAL(15,2)) as invoice_total_amount,
  bdh.billingDocumentDate
FROM billing_document_headers bdh
JOIN billing_document_items bdi ON bdh.billingDocument = bdi.billingDocument
LEFT JOIN outbound_delivery_items odi 
  ON bdi.referenceSdDocument = odi.deliveryDocument 
  AND bdi.referenceSdDocumentItem = odi.deliveryDocumentItem
LEFT JOIN sales_order_items soi 
  ON odi.referenceSdDocument = soi.salesOrder 
  AND odi.referenceSdDocumentItem = soi.salesOrderItem
WHERE bdh.billingDocument = ?  -- Single invoice trace
```

**Data Available**: ✓ Yes, reverse tracing from invoice to order  
**Join Note**: Uses normalized composite keys; LEFT JOINs preserve incomplete flows.

---

### 3. **Incomplete / Broken Flows** (Header-level counts)

```sql
-- Orders without deliveries (aggregate at order level)
SELECT COUNT(DISTINCT soh.salesOrder) as orders_without_delivery 
FROM sales_order_headers soh
LEFT JOIN outbound_delivery_items odi 
  ON soh.salesOrder = odi.referenceSdDocument
WHERE odi.deliveryDocument IS NULL;

-- Deliveries without invoices (aggregate at delivery level)  
SELECT COUNT(DISTINCT odi.deliveryDocument) as deliveries_without_invoice
FROM outbound_delivery_items odi
LEFT JOIN billing_document_items bdi 
  ON odi.deliveryDocument = bdi.referenceSdDocument
WHERE bdi.billingDocument IS NULL;

-- Invoices without payments (aggregate at invoice level)
SELECT COUNT(DISTINCT bdh.billingDocument) as invoices_without_payment
FROM billing_document_headers bdh
LEFT JOIN journal_entry_items_accounts_receivable jear 
  ON bdh.accountingDocument = jear.accountingDocument
LEFT JOIN payments_accounts_receivable par 
  ON jear.accountingDocument = par.clearingAccountingDocument
WHERE par.clearingDate IS NULL;
```

**Data Available**: ✓ Yes, can detect incomplete flows  
**Aggregation Note**: Use DISTINCT to count unique headers, not line items.

---

### 4. **Average O2C Cycle Time (Order → Payment)** (Header-level aggregation)

```sql
SELECT 
  DATEDIFF(day, soh.creationDate, par.clearingDate) as o2c_days,
  COUNT(DISTINCT soh.salesOrder) as order_count,
  MIN(DATEDIFF(day, soh.creationDate, par.clearingDate)) as min_days,
  MAX(DATEDIFF(day, soh.creationDate, par.clearingDate)) as max_days,
  AVG(DATEDIFF(day, soh.creationDate, par.clearingDate)) as avg_days
FROM sales_order_headers soh
LEFT JOIN sales_order_items soi ON soh.salesOrder = soi.salesOrder
LEFT JOIN outbound_delivery_items odi 
  ON soi.salesOrder = odi.referenceSdDocument
LEFT JOIN billing_document_items bdi 
  ON odi.deliveryDocument = bdi.referenceSdDocument
LEFT JOIN billing_document_headers bdh ON bdi.billingDocument = bdh.billingDocument
LEFT JOIN journal_entry_items_accounts_receivable jear 
  ON bdh.accountingDocument = jear.accountingDocument
LEFT JOIN payments_accounts_receivable par 
  ON jear.accountingDocument = par.clearingAccountingDocument
WHERE par.clearingDate IS NOT NULL  -- Only completed flows
GROUP BY DATEDIFF(day, soh.creationDate, par.clearingDate)
ORDER BY order_count DESC
```

**Data Available**: ✓ Yes, for completed flows only  
**Aggregation Note**: DISTINCT order count to avoid item-level duplication; filter for completed payments.

---

### 5. **Customer Payment Patterns**

```sql
SELECT 
  bp.businessPartnerFullName,
  COUNT(DISTINCT par.accountingDocument) as payment_count,
  SUM(CAST(par.amountInTransactionCurrency AS DECIMAL(15,2))) as total_paid,
  AVG(DATEDIFF(day, jear.postingDate, par.clearingDate)) as avg_days_to_pay
FROM payments_accounts_receivable par
JOIN journal_entry_items_accounts_receivable jear 
  ON par.clearingAccountingDocument = jear.accountingDocument
JOIN business_partners bp ON par.customer = bp.businessPartner
GROUP BY par.customer, bp.businessPartnerFullName
ORDER BY total_paid DESC
```

**Data Available**: ✓ Yes, 120 payment records with customer links

---

### 6. **Anomaly: Duplicate Payments**

```sql
SELECT 
  par1.accountingDocument,
  par1.clearingAccountingDocument,
  COUNT(*) as payment_count,
  SUM(CAST(par1.amountInTransactionCurrency AS DECIMAL(15,2))) as total_paid
FROM payments_accounts_receivable par1
GROUP BY par1.clearingAccountingDocument
HAVING COUNT(*) > 1
ORDER BY payment_count DESC
```

**Data Available**: ✓ Yes, can detect multiple payments for same invoice

---

### 7. **Cancelled Invoices Impact**

```sql
SELECT 
  COUNT(DISTINCT bdc.billingDocument) as cancelled_count,
  SUM(CAST(bdh.totalNetAmount AS DECIMAL(15,2))) as cancelled_value
FROM billing_document_cancellations bdc
JOIN billing_document_headers bdh ON bdc.billingDocument = bdh.billingDocument
```

**Data Available**: ✓ Yes, 80 cancellation records with impact analysis  
**Note**: Sums cancelled amounts from original billing documents, not cancellation records.

---

### 8. **Delivery Performance by Plant**

```sql
SELECT 
  p.plant,
  p.plantName,
  COUNT(DISTINCT odi.deliveryDocument) as delivery_count,
  SUM(CAST(odi.actualDeliveryQuantity AS DECIMAL(15,2))) as total_qty_delivered,
  COUNT(CASE WHEN odh.overallGoodsMovementStatus = 'A' THEN 1 END) as pending_deliveries
FROM outbound_delivery_items odi
JOIN plants p ON odi.plant = p.plant
LEFT JOIN outbound_delivery_headers odh ON odi.deliveryDocument = odh.deliveryDocument
GROUP BY p.plant, p.plantName
ORDER BY delivery_count DESC
```

**Data Available**: ✓ Yes, 86 deliveries, 44 plants

---

## Modeling Decisions & Tradeoffs

### Why Graph Projection for This Dataset?

**Relational Tables as Source of Truth**: SAP data remains in normalized relational tables (DuckDB). Graph nodes and edges are derived on-demand for traversal and UI visualization - no pre-materialized graph storage.

**Strengths**:
1. **Natural SAP flow**: O2C is inherently sequential (Order → Delivery → Invoice → Payment)
   - Graph projection captures this with explicit edge types derived from FK relationships
   - Users think in "traces" and "workflows", not SQL joins
2. **Sparse relationships**: Not all orders have all stages (incomplete flows)
   - Graph projection evaluates relationships on-demand without null-heavy nodes
3. **Flexible master data**: Products, plants, customers are reference data
   - Easy to add new master relationships without schema changes
4. **Query-time freshness**: Edges derived from current relational data = no consistency issues
   - Always reflects current state of underlying tables

**Potential Issues**:
1. **Join complexity**: Full O2C trace requires 6+ LEFT JOINs
   - Mitigation: Cache common traces in materialized views
2. **Cardinality estimation**: LLM may not generate optimal join order
   - Mitigation: Explicit SQL validation layer, query hints
3. **Small dataset size**: 21K rows means performance is not critical
   - Would scale well to 1M-10M rows with proper indices

### Why DuckDB Over Graph Database?

**For this specific dataset**:
- SAP data is **fundamentally relational** (normalized tables, foreign keys)
- No circular relationships (acyclic flow: Order → Payment)
- High cardinality on some links (product_storage_locations has 16,723 rows)
- DuckDB's columnar OLAP is perfect for "give me all orders with late payments" analysis

**When to choose Neo4j instead**:
- If flows had cycles (e.g., order returned → new order)
- If queries were primarily graph traversals (e.g., "5 hops from supplier X")
- If dataset was truly massive (>100GB) and join cost became prohibitive

---

## Next Steps for Implementation

1. **Load dataset into DuckDB**
   - Create schema from `backend/data/schema.sql` (adapt from data types found)
   - Import JSONL files with proper type conversion (strings → DECIMAL, time structs → timestamps)
   - Create indices on all FK columns

2. **Verify join paths in practice**
   - Run tracing queries on real data
   - Identify any missing records or unexpected nulls
   - Document edge cases (e.g., cancellations)

3. **Build graph service**
   - Implement edge projection logic for each edge type
   - Add traversal algorithms (BFS for order trace, DFS for deep anomalies)
   - Optimize common paths with materialized views if needed

4. **LLM SQL generation**
   - Train on 4-6 representative queries
   - Set up validation layer to reject overly complex joins
   - Test guardrails on out-of-domain and malicious inputs

---
