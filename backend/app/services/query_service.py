from __future__ import annotations

from typing import Any, Dict, List

from ..db.connection import get_db_connection


class QueryService:
    """Deterministic query service for SAP O2C dataset."""

    def __init__(self, conn=None) -> None:
        self.conn = conn or get_db_connection()

    @staticmethod
    def _normalize_item_expr(column_sql: str) -> str:
        """Normalize item identifiers to 6-char zero-padded strings."""
        return f"lpad(CAST({column_sql} AS VARCHAR), 6, '0')"

    def top_products_by_billing_count(self, limit: int = 10) -> Dict[str, Any]:
        """Return products ranked by distinct billing document count."""
        rows = self.conn.execute(
            f"""
            SELECT
                bdi.material AS product,
                COUNT(DISTINCT bdi.billingdocument) AS billing_document_count
            FROM billing_document_items bdi
            WHERE bdi.material IS NOT NULL
            GROUP BY bdi.material
            ORDER BY billing_document_count DESC, product ASC
            LIMIT {int(limit)}
            """
        ).fetchall()

        return {
            "limit": int(limit),
            "results": [
                {
                    "product": row[0],
                    "billing_document_count": int(row[1]),
                }
                for row in rows
            ],
        }

    def broken_flows(self) -> Dict[str, Any]:
        """Return broken / incomplete O2C flow buckets."""
        delivered_not_billed = self.conn.execute(
            f"""
            SELECT DISTINCT odi.deliverydocument
            FROM outbound_delivery_items odi
            LEFT JOIN billing_document_items bdi
              ON odi.deliverydocument = bdi.referencesddocument
             AND {self._normalize_item_expr('odi.deliverydocumentitem')}
                 = {self._normalize_item_expr('bdi.referencesddocumentitem')}
            WHERE bdi.billingdocument IS NULL
            ORDER BY odi.deliverydocument
            """
        ).fetchall()

        billed_without_delivery = self.conn.execute(
            f"""
            SELECT DISTINCT bdi.billingdocument
            FROM billing_document_items bdi
            LEFT JOIN outbound_delivery_items odi
              ON odi.deliverydocument = bdi.referencesddocument
             AND {self._normalize_item_expr('odi.deliverydocumentitem')}
                 = {self._normalize_item_expr('bdi.referencesddocumentitem')}
            WHERE odi.deliverydocument IS NULL
            ORDER BY bdi.billingdocument
            """
        ).fetchall()

        sales_orders_no_downstream = self.conn.execute(
            f"""
            SELECT DISTINCT soh.salesorder
            FROM sales_order_headers soh
            LEFT JOIN sales_order_items soi
              ON soh.salesorder = soi.salesorder
            LEFT JOIN outbound_delivery_items odi
              ON soi.salesorder = odi.referencesddocument
             AND {self._normalize_item_expr('soi.salesorderitem')}
                 = {self._normalize_item_expr('odi.referencesddocumentitem')}
            WHERE odi.deliverydocument IS NULL
            ORDER BY soh.salesorder
            """
        ).fetchall()

        return {
            "delivered_but_not_billed": {
                "count": len(delivered_not_billed),
                "sample_ids": [row[0] for row in delivered_not_billed[:20]],
            },
            "billed_without_delivery": {
                "count": len(billed_without_delivery),
                "sample_ids": [row[0] for row in billed_without_delivery[:20]],
            },
            "sales_orders_with_no_downstream_flow": {
                "count": len(sales_orders_no_downstream),
                "sample_ids": [row[0] for row in sales_orders_no_downstream[:20]],
            },
        }

    def trace_billing_flow(self, billing_document_id: str) -> Dict[str, Any]:
        """Trace a billing document through billing, delivery, order, and journal entry."""
        header = self.conn.execute(
            """
            SELECT billingdocument, accountingdocument, soldtoparty
            FROM billing_document_headers
            WHERE billingdocument = ?
            """,
            [billing_document_id],
        ).fetchone()

        if not header:
            raise ValueError(f"Billing document {billing_document_id} not found.")

        rows = self.conn.execute(
            f"""
            SELECT
                bdi.billingdocument,
                bdi.billingdocumentitem,
                bdi.referencesddocument AS deliverydocument,
                bdi.referencesddocumentitem AS deliverydocumentitem,
                odi.referencesddocument AS salesorder,
                odi.referencesddocumentitem AS salesorderitem,
                bdh.accountingdocument,
                bdh.soldtoparty
            FROM billing_document_items bdi
            LEFT JOIN outbound_delivery_items odi
              ON odi.deliverydocument = bdi.referencesddocument
             AND {self._normalize_item_expr('odi.deliverydocumentitem')}
                 = {self._normalize_item_expr('bdi.referencesddocumentitem')}
            LEFT JOIN billing_document_headers bdh
              ON bdi.billingdocument = bdh.billingdocument
            WHERE bdi.billingdocument = ?
            ORDER BY bdi.billingdocumentitem
            """,
            [billing_document_id],
        ).fetchall()

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        seen_nodes = set()
        seen_edges = set()

        def add_node(node_id: str, node_type: str, label: str, metadata: Dict[str, Any] | None = None) -> None:
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append(
                    {
                        "node_id": node_id,
                        "node_type": node_type,
                        "label": label,
                        "metadata": metadata or {},
                    }
                )

        def add_edge(edge_id: str, source_id: str, target_id: str, edge_type: str) -> None:
            if edge_id not in seen_edges:
                seen_edges.add(edge_id)
                edges.append(
                    {
                        "edge_id": edge_id,
                        "source_id": source_id,
                        "target_id": target_id,
                        "edge_type": edge_type,
                    }
                )

        billing_doc_id, accounting_doc, sold_to_party = header

        add_node(
            f"billingdocument_{billing_doc_id}",
            "BillingDocument",
            f"Invoice {billing_doc_id}",
            {
                "billingdocument": billing_doc_id,
                "accountingdocument": accounting_doc,
                "soldtoparty": sold_to_party,
            },
        )

        if sold_to_party:
            add_node(
                f"customer_{sold_to_party}",
                "Customer",
                str(sold_to_party),
                {"businesspartner": sold_to_party},
            )
            add_edge(
                f"billing_document_for_customer_{billing_doc_id}",
                f"billingdocument_{billing_doc_id}",
                f"customer_{sold_to_party}",
                "BILLING_DOCUMENT_FOR_CUSTOMER",
            )

        if accounting_doc:
            je_rows = self.conn.execute(
                """
                SELECT accountingdocument, accountingdocumentitem
                FROM journal_entry_items_accounts_receivable
                WHERE accountingdocument = ?
                ORDER BY accountingdocumentitem
                """,
                [accounting_doc],
            ).fetchall()

            for je in je_rows:
                je_node_id = f"journalentry_{je[0]}_{je[1]}"
                add_node(
                    je_node_id,
                    "JournalEntry",
                    f"JE {je[0]}",
                    {
                        "accountingdocument": je[0],
                        "accountingdocumentitem": je[1],
                    },
                )
                add_edge(
                    f"billing_document_posted_to_journal_entry_{billing_doc_id}_{je[0]}_{je[1]}",
                    f"billingdocument_{billing_doc_id}",
                    je_node_id,
                    "BILLING_DOCUMENT_POSTED_TO_JOURNAL_ENTRY",
                )

        for row in rows:
            (
                billingdocument,
                billingdocumentitem,
                deliverydocument,
                deliverydocumentitem,
                salesorder,
                salesorderitem,
                _accountingdocument,
                _soldtoparty,
            ) = row

            billing_item_id = f"billingitem_{billingdocument}_{str(billingdocumentitem).zfill(6)}"
            add_node(
                billing_item_id,
                "BillingItem",
                f"Item {billingdocumentitem}",
                {
                    "billingdocument": billingdocument,
                    "billingdocumentitem": billingdocumentitem,
                },
            )
            add_edge(
                f"billing_item_in_document_{billingdocument}_{str(billingdocumentitem).zfill(6)}",
                billing_item_id,
                f"billingdocument_{billingdocument}",
                "BILLING_ITEM_IN_DOCUMENT",
            )

            if deliverydocument:
                delivery_id = f"delivery_{deliverydocument}"
                delivery_item_id = f"deliveryitem_{deliverydocument}_{str(deliverydocumentitem).zfill(6)}"

                add_node(
                    delivery_id,
                    "Delivery",
                    f"Delivery {deliverydocument}",
                    {"deliverydocument": deliverydocument},
                )
                add_node(
                    delivery_item_id,
                    "DeliveryItem",
                    f"Item {deliverydocumentitem}",
                    {
                        "deliverydocument": deliverydocument,
                        "deliverydocumentitem": deliverydocumentitem,
                    },
                )

                add_edge(
                    f"delivery_item_in_delivery_{deliverydocument}_{str(deliverydocumentitem).zfill(6)}",
                    delivery_item_id,
                    delivery_id,
                    "DELIVERY_ITEM_IN_DELIVERY",
                )
                add_edge(
                    f"delivery_item_billed_by_billing_item_{deliverydocument}_{str(deliverydocumentitem).zfill(6)}_{billingdocument}_{str(billingdocumentitem).zfill(6)}",
                    delivery_item_id,
                    billing_item_id,
                    "DELIVERY_ITEM_BILLED_BY_BILLING_ITEM",
                )

            if salesorder:
                sales_order_id = f"salesorder_{salesorder}"
                sales_order_item_id = f"salesorderitem_{salesorder}_{str(salesorderitem).zfill(6)}"

                add_node(
                    sales_order_id,
                    "SalesOrder",
                    f"Order {salesorder}",
                    {"salesorder": salesorder},
                )
                add_node(
                    sales_order_item_id,
                    "SalesOrderItem",
                    f"Item {salesorderitem}",
                    {
                        "salesorder": salesorder,
                        "salesorderitem": salesorderitem,
                    },
                )

                add_edge(
                    f"order_has_item_{salesorder}_{str(salesorderitem).zfill(6)}",
                    sales_order_id,
                    sales_order_item_id,
                    "ORDER_HAS_ITEM",
                )

                if deliverydocument:
                    add_edge(
                        f"item_fulfilled_by_delivery_item_{salesorder}_{str(salesorderitem).zfill(6)}_{deliverydocument}_{str(deliverydocumentitem).zfill(6)}",
                        sales_order_item_id,
                        f"deliveryitem_{deliverydocument}_{str(deliverydocumentitem).zfill(6)}",
                        "ITEM_FULFILLED_BY_DELIVERY_ITEM",
                    )

        return {
            "billing_document_id": billing_document_id,
            "summary": {
                "nodes": len(nodes),
                "edges": len(edges),
            },
            "nodes": nodes,
            "edges": edges,
        }