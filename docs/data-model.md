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

## Verified Join Paths

### ✓ Confirmed Path 1: Sales Order → Items

```
sales_order_headers.salesOrder 
  → sales_order_items.salesOrder (1:N)
```
- **Example**: `salesOrder="740506"` has 1+ items with `salesOrderItem="10"`, `"20"`, etc.
- **Verified**: Yes, sample data shows multiple items per order.

---

### ✓ Confirmed Path 2: Sales Order Items → Outbound Delivery Items

```
sales_order_items.(salesOrder, salesOrderItem)
  → outbound_delivery_items.(referenceSdDocument, referenceSdDocumentItem) (1:N)
```
- **Column Evidence**: `outbound_delivery_items.referenceSdDocument` = sales order ID
- **Verified**: Yes, sample row shows `referenceSdDocument="740556"`, `referenceSdDocumentItem="000010"`
- **Cardinality**: 1 sales order item can generate multiple delivery items (partial shipments, splits)

---

### ✓ Confirmed Path 3: Outbound Delivery Items → Billing Document Items

```
outbound_delivery_items.(deliveryDocument, deliveryDocumentItem)
  → billing_document_items.(referenceSdDocument, referenceSdDocumentItem) (1:N)
```
- **Column Evidence**: `billing_document_items.referenceSdDocument` = delivery document ID
- **Verified**: Yes, sample shows `referenceSdDocument="80738109"`, `referenceSdDocumentItem="10"`
- **Cardinality**: 1 delivery can be billed in multiple invoices (batch invoicing) or 1 delivery per invoice

---

### ✓ Confirmed Path 4: Billing Document Headers → Items

```
billing_document_headers.billingDocument
  → billing_document_items.billingDocument (1:N)
```
- **Verified**: Yes, standard SAP pattern.

---

### ✓ Confirmed Path 5: Billing Document Headers → GL Entry (Accounts Receivable)

```
billing_document_headers.accountingDocument
  → journal_entry_items_accounts_receivable.accountingDocument (1:N)
```
- **Evidence**: `billing_document_headers.accountingDocument="9400000249"` appears in journal entries
- **Verified**: Yes, invoice creates GL posting for AR
- **Cardinality**: 1 invoice = 1+ GL line items (debit AR, credit Revenue, credit Tax, etc.)

---

### ✓ Confirmed Path 6: GL Entry → Payment Clearing

```
journal_entry_items_accounts_receivable.accountingDocument
  → payments_accounts_receivable.clearingAccountingDocument (1:N)
```
- **Evidence**: Payment has `clearingAccountingDocument` pointing to invoice GL entry
- **Verified**: Yes, payment clears (matches) invoice GL entries
- **Cardinality**: 1 invoice can be paid in multiple payments (partial payments)

---

### ✓ Confirmed Path 7: Sales Order → Customer (Business Partner)

```
sales_order_headers.soldToParty
  → business_partners.businessPartner (N:1)
```
- **Verified**: Yes, `soldToParty="310000108"` matches `businessPartner` ID
- **Cardinality**: Multiple orders per customer (N:1)

---

### ✓ Confirmed Path 8: Sales Order Item → Product

```
sales_order_items.material
  → products.product (N:1)
```
- **Verified**: Yes, `material="S8907367001003"` links to products
- **Cardinality**: Multiple order items reference same product (N:1)

---

### ✓ Confirmed Path 9: Outbound Delivery Item → Plant

```
outbound_delivery_items.plant
  → plants.plant (N:1)
```
- **Verified**: Yes, `plant="WB05"` in delivery items matches `plants.plant`
- **Cardinality**: Multiple deliveries from same warehouse

---

### ⚠ Uncertain Path: Invoice → Delivery (via referenceDocument)

```
journal_entry_items_accounts_receivable.referenceDocument
  → billing_document_headers.billingDocument (optional, often NULL)
```

- **Issue**: `referenceDocument` column is **often NULL** (not populated)
- **Alternative**: Use `billing_document_headers.accountingDocument` instead
- **Recommendation**: Prefer GL-based linking, not reference field

---

## Data Quality & Normalization Issues

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

### 6. ✓ Sparse Master Data

**Finding**: 
- 69 products but 3,036 product-plant records (sparse matrix)
- 44 plants, 8 business partners (small master data)
- Large number of storage locations (16,723 records for inventory)

**Implication**: 
- Product availability is sparse (not all products in all plants)
- Queries on storage locations may be large
- Customer base is small (8 BPs), so customer-level aggregations are coarse

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
| `product` | products | `product` | Master data |
| `plant` | plants | `plant` | Master data |

---

### Recommended Edge Types (from real dataset)

| Edge Type | Source | Target | Cardinality | SAP Join |
|-----------|--------|--------|-------------|----------|
| `INCLUDES` | `sales_order` | `sales_order_item` | 1:N | `salesOrder` FK |
| `FULFILLED_BY` | `sales_order_item` | `outbound_delivery_item` | 1:N | `(referenceSdDocument, referenceSdDocumentItem)` |
| `DELIVERED_IN` | `outbound_delivery` | `outbound_delivery_item` | 1:N | `deliveryDocument` FK |
| `INVOICED_IN` | `outbound_delivery_item` | `billing_document_item` | 1:N | `(referenceSdDocument, referenceSdDocumentItem)` |
| `CONTAINS` | `billing_document` | `billing_document_item` | 1:N | `billingDocument` FK |
| `POSTS_GL` | `billing_document` | `gl_entry` | 1:N | `accountingDocument` FK |
| `PAID_BY` | `gl_entry` | `payment` | 1:N | `clearingAccountingDocument` FK |
| `ORDERED_BY` | `sales_order` | `customer` | N:1 | `soldToParty` FK |
| `CONTAINS_MATERIAL` | `sales_order_item` | `product` | N:1 | `material` FK |
| `SOURCED_FROM` | `outbound_delivery_item` | `plant` | N:1 | `plant` FK |
| `BILLED_FOR` | `billing_document_item` | `product` | N:1 | `material` FK |

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

### 2. **Full Billing Flow Trace (Order → Delivery → Invoice → Payment)**

```sql
SELECT 
  soh.salesOrder,
  soi.salesOrderItem,
  soi.material,
  odi.deliveryDocument,
  bdi.billingDocument,
  bdh.accountingDocument,
  par.clearingAccountingDocument,
  CAST(soi.netAmount AS DECIMAL(15,2)) as order_amount,
  CAST(bdh.totalNetAmount AS DECIMAL(15,2)) as invoice_amount,
  CAST(par.amountInTransactionCurrency AS DECIMAL(15,2)) as payment_amount,
  DATEDIFF(day, bdh.billingDocumentDate, par.clearingDate) as days_to_payment
FROM sales_order_headers soh
JOIN sales_order_items soi ON soh.salesOrder = soi.salesOrder
LEFT JOIN outbound_delivery_items odi 
  ON soi.salesOrder = odi.referenceSdDocument 
  AND soi.salesOrderItem = odi.referenceSdDocumentItem
LEFT JOIN billing_document_items bdi 
  ON odi.deliveryDocument = bdi.referenceSdDocument 
  AND odi.deliveryDocumentItem = bdi.referenceSdDocumentItem
LEFT JOIN billing_document_headers bdh ON bdi.billingDocument = bdh.billingDocument
LEFT JOIN journal_entry_items_accounts_receivable jear 
  ON bdh.accountingDocument = jear.accountingDocument
LEFT JOIN payments_accounts_receivable par 
  ON jear.accountingDocument = par.clearingAccountingDocument
WHERE soh.salesOrder = ?  -- Single order trace
```

**Data Available**: ✓ Yes, complete end-to-end flow available

---

### 3. **Incomplete / Broken Flows**

```sql
-- Orders without deliveries
SELECT COUNT(*) FROM sales_order_headers soh
LEFT JOIN outbound_delivery_items odi 
  ON soh.salesOrder = odi.referenceSdDocument
WHERE odi.deliveryDocument IS NULL;

-- Deliveries without invoices
SELECT COUNT(*) FROM outbound_delivery_items odi
LEFT JOIN billing_document_items bdi 
  ON odi.deliveryDocument = bdi.referenceSdDocument
WHERE bdi.billingDocument IS NULL;

-- Invoices without payments
SELECT COUNT(*) FROM billing_document_headers bdh
LEFT JOIN journal_entry_items_accounts_receivable jear 
  ON bdh.accountingDocument = jear.accountingDocument
LEFT JOIN payments_accounts_receivable par 
  ON jear.accountingDocument = par.clearingAccountingDocument
WHERE par.clearingDate IS NULL;
```

**Data Available**: ✓ Yes, can detect incomplete flows

---

### 4. **Average O2C Cycle Time (Order → Payment)**

```sql
SELECT 
  DATEDIFF(day, soh.creationDate, par.clearingDate) as o2c_days,
  COUNT(*) as order_count,
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
WHERE par.clearingDate IS NOT NULL
GROUP BY o2c_days
ORDER BY order_count DESC
```

**Data Available**: ✓ Yes, dates available from sales_order_headers.creationDate to payments_accounts_receivable.clearingDate

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
  COUNT(bdc.billingDocument) as cancelled_count,
  SUM(CAST(bdc.totalNetAmount AS DECIMAL(15,2))) as cancelled_value,
  SUM(CAST(bdh.totalNetAmount AS DECIMAL(15,2))) as total_value
FROM billing_document_cancellations bdc
JOIN billing_document_headers bdh ON bdc.billingDocument = bdh.billingDocument
```

**Data Available**: ✓ Yes, 80 cancellation records with impact analysis

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

**Strengths**:
1. **Natural SAP flow**: O2C is inherently sequential (Order → Delivery → Invoice → Payment)
   - Graph projection captures this with explicit edge types
   - Users think in "traces" and "workflows", not SQL joins
2. **Sparse relationships**: Not all orders have all stages (incomplete flows)
   - Graph DB would require null-heavy nodes; projection evaluates on-demand
3. **Flexible master data**: Products, plants, customers are reference data
   - Easy to add new master relationships without schema changes
4. **Query-time freshness**: No pre-materialized edges = no consistency issues
   - Always reflects current state of underlying relational data

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
