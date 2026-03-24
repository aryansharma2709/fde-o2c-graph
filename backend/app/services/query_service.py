from typing import List, Dict, Any, Optional
from duckdb import DuckDBPyConnection

class QueryService:
    def __init__(self, conn: DuckDBPyConnection):
        self.conn = conn

    def top_products_by_billing_count(self, limit: int = 10) -> List[Dict[str, Any]]:
        sql = """
            SELECT
                soi.material AS product,
                COUNT(DISTINCT bdi.billingdocument) AS billing_document_count
            FROM sales_order_items soi
            JOIN billing_document_items bdi
              ON soi.salesorder = bdi.referencesddocument
             AND lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') = lpad(CAST(bdi.referencesddocumentitem AS VARCHAR), 6, '0')
            WHERE soi.material IS NOT NULL
            GROUP BY soi.material
            ORDER BY billing_document_count DESC
            LIMIT ?
        """
        rows = self.conn.execute(sql, [limit]).fetchall()
        return [
            {"product": row[0], "billing_document_count": row[1]} for row in rows
        ]

    def trace_billing_flow(self, billing_document_id: str) -> Dict[str, Any]:
        # Find all nodes and edges in the billing flow
        nodes = {}
        edges = []
        summary = {}
        # 1. Billing Document
        bdh = self.conn.execute(
            """
            SELECT billingdocument, soldtoparty, accountingdocument
            FROM billing_document_headers
            WHERE billingdocument = ?
            """,
            [billing_document_id],
        ).fetchone()
        if not bdh:
            return {"error": "Billing document not found"}
        nodes["billing_document"] = {
            "id": bdh[0],
            "type": "BillingDocument",
            "customer": bdh[1],
            "accounting_document": bdh[2],
        }
        # 2. Billing Items
        billing_items = self.conn.execute(
            """
            SELECT billingdocumentitem, material, referencesddocument, referencesddocumentitem
            FROM billing_document_items
            WHERE billingdocument = ?
            """,
            [billing_document_id],
        ).fetchall()
        nodes["billing_items"] = [
            {
                "id": f"{billing_document_id}_{item[0]}",
                "type": "BillingItem",
                "material": item[1],
                "referencesddocument": item[2],
                "referencesddocumentitem": item[3],
            }
            for item in billing_items
        ]
        # 3. Delivery Items
        delivery_items = []
        for item in billing_items:
            delivery = self.conn.execute(
                """
                SELECT deliverydocument, deliverydocumentitem, plant
                FROM outbound_delivery_items
                WHERE referencesddocument = ?
                  AND lpad(CAST(referencesddocumentitem AS VARCHAR), 6, '0') = lpad(CAST(? AS VARCHAR), 6, '0')
                """,
                [item[2], item[3]],
            ).fetchone()
            if delivery:
                delivery_items.append({
                    "id": f"{delivery[0]}_{delivery[1]}",
                    "type": "DeliveryItem",
                    "deliverydocument": delivery[0],
                    "deliverydocumentitem": delivery[1],
                    "plant": delivery[2],
                })
        nodes["delivery_items"] = delivery_items
        # 4. Deliveries
        deliveries = []
        for di in delivery_items:
            delivery = self.conn.execute(
                """
                SELECT deliverydocument, shippingpoint
                FROM outbound_delivery_headers
                WHERE deliverydocument = ?
                """,
                [di["deliverydocument"]],
            ).fetchone()
            if delivery:
                deliveries.append({
                    "id": delivery[0],
                    "type": "Delivery",
                    "shippingpoint": delivery[1],
                })
        nodes["deliveries"] = deliveries
        # 5. Sales Order Items
        sales_order_items = []
        for item in billing_items:
            soi = self.conn.execute(
                """
                SELECT salesorder, salesorderitem, material
                FROM sales_order_items
                WHERE salesorder = ?
                  AND lpad(CAST(salesorderitem AS VARCHAR), 6, '0') = lpad(CAST(? AS VARCHAR), 6, '0')
                """,
                [item[2], item[3]],
            ).fetchone()
            if soi:
                sales_order_items.append({
                    "id": f"{soi[0]}_{soi[1]}",
                    "type": "SalesOrderItem",
                    "salesorder": soi[0],
                    "salesorderitem": soi[1],
                    "material": soi[2],
                })
        nodes["sales_order_items"] = sales_order_items
        # 6. Sales Orders
        sales_orders = []
        for soi in sales_order_items:
            so = self.conn.execute(
                """
                SELECT salesorder, soldtoparty
                FROM sales_order_headers
                WHERE salesorder = ?
                """,
                [soi["salesorder"]],
            ).fetchone()
            if so:
                sales_orders.append({
                    "id": so[0],
                    "type": "SalesOrder",
                    "soldtoparty": so[1],
                })
        nodes["sales_orders"] = sales_orders
        # 7. Journal Entry
        journal_entry = None
        if bdh[2]:
            je = self.conn.execute(
                """
                SELECT accountingdocument, accountingdocumentitem, amountintransactioncurrency
                FROM journal_entry_items_accounts_receivable
                WHERE accountingdocument = ?
                LIMIT 1
                """,
                [bdh[2]],
            ).fetchone()
            if je:
                journal_entry = {
                    "id": f"{je[0]}_{je[1]}",
                    "type": "JournalEntry",
                    "amount": je[2],
                }
        nodes["journal_entry"] = journal_entry
        # Edges (simple, for UI highlighting)
        # (BillingDocument -> BillingItem -> DeliveryItem -> Delivery -> SalesOrderItem -> SalesOrder -> JournalEntry)
        # Build edges as (source_id, target_id, type)
        edges = []
        for item in nodes["billing_items"]:
            edges.append({
                "source": bdh[0],
                "target": item["id"],
                "type": "HAS_BILLING_ITEM",
            })
        for di in nodes["delivery_items"]:
            for item in nodes["billing_items"]:
                edges.append({
                    "source": item["id"],
                    "target": di["id"],
                    "type": "BILLED_DELIVERY_ITEM",
                })
        for d in nodes["deliveries"]:
            for di in nodes["delivery_items"]:
                edges.append({
                    "source": di["id"],
                    "target": d["id"],
                    "type": "DELIVERY_OF_ITEM",
                })
        for soi in nodes["sales_order_items"]:
            for item in nodes["billing_items"]:
                edges.append({
                    "source": item["id"],
                    "target": soi["id"],
                    "type": "BILLED_SALES_ORDER_ITEM",
                })
        for so in nodes["sales_orders"]:
            for soi in nodes["sales_order_items"]:
                edges.append({
                    "source": soi["id"],
                    "target": so["id"],
                    "type": "SALES_ORDER_OF_ITEM",
                })
        if journal_entry:
            for so in nodes["sales_orders"]:
                edges.append({
                    "source": so["id"],
                    "target": journal_entry["id"],
                    "type": "POSTED_TO_JOURNAL_ENTRY",
                })
        summary = {
            "billing_document": bdh[0],
            "customer": bdh[1],
            "accounting_document": bdh[2],
            "billing_items": len(nodes["billing_items"]),
            "delivery_items": len(nodes["delivery_items"]),
            "sales_order_items": len(nodes["sales_order_items"]),
            "sales_orders": len(nodes["sales_orders"]),
            "journal_entry": bool(journal_entry),
        }
        return {"nodes": nodes, "edges": edges, "summary": summary}

    def broken_flows(self) -> Dict[str, Any]:
        # Delivered but not billed
        delivered_not_billed = self.conn.execute(
            """
            SELECT DISTINCT odi.deliverydocument
            FROM outbound_delivery_items odi
            LEFT JOIN billing_document_items bdi
              ON odi.deliverydocument = bdi.referencesddocument
             AND lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') = lpad(CAST(bdi.referencesddocumentitem AS VARCHAR), 6, '0')
            WHERE bdi.billingdocument IS NULL
            """
        ).fetchall()
        # Billed without delivery
        billed_without_delivery = self.conn.execute(
            """
            SELECT DISTINCT bdi.billingdocument
            FROM billing_document_items bdi
            LEFT JOIN outbound_delivery_items odi
              ON bdi.referencesddocument = odi.deliverydocument
             AND lpad(CAST(bdi.referencesddocumentitem AS VARCHAR), 6, '0') = lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0')
            WHERE odi.deliverydocument IS NULL
            """
        ).fetchall()
        # Sales orders with no downstream flow
        sales_orders_no_flow = self.conn.execute(
            """
            SELECT soh.salesorder
            FROM sales_order_headers soh
            LEFT JOIN sales_order_items soi ON soh.salesorder = soi.salesorder
            LEFT JOIN outbound_delivery_items odi ON soi.salesorder = odi.referencesddocument
             AND lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') = lpad(CAST(odi.referencesddocumentitem AS VARCHAR), 6, '0')
            LEFT JOIN billing_document_items bdi ON soi.salesorder = bdi.referencesddocument
             AND lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') = lpad(CAST(bdi.referencesddocumentitem AS VARCHAR), 6, '0')
            WHERE odi.deliverydocument IS NULL AND bdi.billingdocument IS NULL
            GROUP BY soh.salesorder
            """
        ).fetchall()
        return {
            "delivered_not_billed": [row[0] for row in delivered_not_billed],
            "billed_without_delivery": [row[0] for row in billed_without_delivery],
            "sales_orders_no_flow": [row[0] for row in sales_orders_no_flow],
        }
