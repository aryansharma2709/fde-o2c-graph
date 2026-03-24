"""Graph service for building and querying graph projections from SAP O2C data."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..db.connection import get_db_connection


class GraphService:
    """Service for graph operations on SAP O2C data."""

    def __init__(self, conn=None) -> None:
        self.conn = conn or get_db_connection()

    @staticmethod
    def _parse_json(value: Any) -> Dict[str, Any]:
        """Safely parse JSON values coming back from DuckDB."""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return {"raw": value}
        return {"raw": value}

    def build_graph_nodes(self) -> int:
        """Build graph nodes from relational tables and return node count."""
        self.conn.execute("DELETE FROM graph_nodes")

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'customer_' || businessPartner AS node_id,
                'Customer' AS node_type,
                COALESCE(businessPartnerFullName, businessPartnerName, businessPartner) AS label,
                json_object(
                    'businessPartner', businessPartner,
                    'name', businessPartnerFullName,
                    'category', businessPartnerCategory
                ) AS metadata_json
            FROM business_partners
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'address_' || businesspartner || '_' || addressid AS node_id,
                'Address' AS node_type,
                COALESCE(cityname, 'Address ' || addressid) AS label,
                json_object(
                    'business_partner', businesspartner,
                    'address_id', addressid,
                    'street', streetname,
                    'city', cityname,
                    'postal_code', postalcode,
                    'country', country
                ) AS metadata_json
            FROM business_partner_addresses
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'salesorder_' || salesorder AS node_id,
                'SalesOrder' AS node_type,
                'Order ' || salesorder AS label,
                json_object(
                    'sales_order', salesorder,
                    'type', salesordertype,
                    'date', creationdate,
                    'total_amount', totalnetamount,
                    'currency', transactioncurrency,
                    'status', overalldeliverystatus,
                    'customer', soldtoparty
                ) AS metadata_json
            FROM sales_order_headers
            """
        )

        self.conn.execute(
    """
    INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
    SELECT DISTINCT
        'salesorderitem_' || salesorder || '_' || lpad(CAST(salesorderitem AS VARCHAR), 6, '0') AS node_id,
        'SalesOrderItem' AS node_type,
        'Item ' || salesorderitem AS label,
        json_object(
            'sales_order', salesorder,
            'item', salesorderitem,
            'material', material,
            'quantity', requestedquantity,
            'net_amount', netamount,
            'currency', transactioncurrency
        ) AS metadata_json
    FROM sales_order_items
    """
)

        self.conn.execute(
    """
    INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
    SELECT DISTINCT
        'product_' || product AS node_id,
        'Product' AS node_type,
        product AS label,
        json_object(
            'product', product
        ) AS metadata_json
    FROM products
    """
)

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'delivery_' || deliveryDocument AS node_id,
                'Delivery' AS node_type,
                'Delivery ' || deliveryDocument AS label,
                json_object(
                    'deliveryDocument', deliveryDocument,
                    'shippingPoint', shippingPoint
                ) AS metadata_json
            FROM outbound_delivery_headers
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'deliveryitem_' || deliveryDocument || '_' || lpad(CAST(deliveryDocumentItem AS VARCHAR), 6, '0') AS node_id,
                'DeliveryItem' AS node_type,
                'Item ' || deliveryDocumentItem AS label,
                json_object(
                    'deliveryDocument', deliveryDocument,
                    'item', deliveryDocumentItem,
                    'actualDeliveryQuantity', actualDeliveryQuantity,
                    'referenceSdDocument', referenceSdDocument,
                    'referenceSdDocumentItem', referenceSdDocumentItem,
                    'plant', plant
                ) AS metadata_json
            FROM outbound_delivery_items
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'plant_' || plant AS node_id,
                'Plant' AS node_type,
                COALESCE(plantName, plant) AS label,
                json_object(
                    'plant', plant,
                    'name', plantName,
                    'address_id', addressId,
                    'plantCategory', plantCategory,
                    'factoryCalendar', factoryCalendar,
                    'salesOrganization', salesOrganization,
                    'distributionChannel', distributionChannel,
                    'division', division
                ) AS metadata_json
            FROM plants
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'billingdocument_' || billingdocument AS node_id,
                'BillingDocument' AS node_type,
                'Invoice ' || billingdocument AS label,
                json_object(
                    'billing_document', billingdocument,
                    'type', billingdocumenttype,
                    'date', billingdocumentdate,
                    'net_amount', totalnetamount,
                    'currency', transactioncurrency,
                    'is_cancelled', billingdocumentiscancelled,
                    'customer', soldtoparty,
                    'accounting_document', accountingdocument
                ) AS metadata_json
            FROM billing_document_headers
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'billingitem_' || billingdocument || '_' || lpad(CAST(billingdocumentitem AS VARCHAR), 6, '0') AS node_id,
                'BillingItem' AS node_type,
                'Item ' || billingdocumentitem AS label,
                json_object(
                    'billing_document', billingdocument,
                    'item', billingdocumentitem,
                    'material', material,
                    'net_amount', netamount,
                    'sales_order', referencesddocument,
                    'sales_order_item', referencesddocumentitem
                ) AS metadata_json
            FROM billing_document_items
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'journalentry_' || accountingdocument || '_' || CAST(accountingdocumentitem AS VARCHAR) AS node_id,
                'JournalEntry' AS node_type,
                'JE ' || accountingdocument AS label,
                json_object(
                    'accounting_document', accountingdocument,
                    'item', accountingdocumentitem,
                    'date', postingdate,
                    'amount', amountintransactioncurrency,
                    'currency', transactioncurrency,
                    'customer', customer
                ) AS metadata_json
            FROM journal_entry_items_accounts_receivable
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_nodes (node_id, node_type, label, metadata_json)
            SELECT DISTINCT
                'payment_' || accountingdocument AS node_id,
                'Payment' AS node_type,
                'Payment ' || accountingdocument AS label,
                json_object(
                    'accounting_document', accountingdocument,
                    'clearing_date', clearingdate,
                    'amount', amountintransactioncurrency,
                    'currency', transactioncurrency,
                    'clearing_accounting_document', clearingaccountingdocument
                ) AS metadata_json
            FROM payments_accounts_receivable
            """
        )

        self.conn.commit()
        result = self.conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()
        return int(result[0]) if result else 0

    def build_graph_edges(self) -> int:
        """Build graph edges from relational relationships and return edge count."""
        self.conn.execute("DELETE FROM graph_edges")

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'customer_placed_order_' || soh.salesorder AS edge_id,
                'customer_' || soh.soldtoparty AS source_id,
                'salesorder_' || soh.salesorder AS target_id,
                'CUSTOMER_PLACED_ORDER' AS edge_type,
                json_object('relationship', 'customer_order') AS metadata_json
            FROM sales_order_headers soh
            WHERE soh.soldtoparty IS NOT NULL
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'order_has_item_' || soi.salesorder || '_' || lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') AS edge_id,
                'salesorder_' || soi.salesorder AS source_id,
                'salesorderitem_' || soi.salesorder || '_' || lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') AS target_id,
                'ORDER_HAS_ITEM' AS edge_type,
                json_object('quantity', soi.requestedquantity) AS metadata_json
            FROM sales_order_items soi
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'item_for_product_' || soi.salesorder || '_' || lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') AS edge_id,
                'salesorderitem_' || soi.salesorder || '_' || lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') AS source_id,
                'product_' || soi.material AS target_id,
                'ITEM_FOR_PRODUCT' AS edge_type,
                json_object('material', soi.material) AS metadata_json
            FROM sales_order_items soi
            WHERE soi.material IS NOT NULL
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'item_fulfilled_by_delivery_item_' || soi.salesorder || '_' || lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0')
                    || '_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') AS edge_id,
                'salesorderitem_' || soi.salesorder || '_' || lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0') AS source_id,
                'deliveryitem_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') AS target_id,
                'ITEM_FULFILLED_BY_DELIVERY_ITEM' AS edge_type,
                json_object(
                    'fulfilled_quantity', odi.actualdeliveryquantity,
                    'delivery_document', odi.deliverydocument
                ) AS metadata_json
            FROM sales_order_items soi
            JOIN outbound_delivery_items odi
              ON soi.salesorder = odi.referencesddocument
             AND lpad(CAST(soi.salesorderitem AS VARCHAR), 6, '0')
                 = lpad(CAST(odi.referencesddocumentitem AS VARCHAR), 6, '0')
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'delivery_item_in_delivery_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') AS edge_id,
                'deliveryitem_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') AS source_id,
                'delivery_' || odi.deliverydocument AS target_id,
                'DELIVERY_ITEM_IN_DELIVERY' AS edge_type,
                json_object('relationship', 'parent_child') AS metadata_json
            FROM outbound_delivery_items odi
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'delivery_item_from_plant_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') AS edge_id,
                'deliveryitem_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') AS source_id,
                'plant_' || odi.plant AS target_id,
                'DELIVERY_ITEM_FROM_PLANT' AS edge_type,
                json_object('plant', odi.plant) AS metadata_json
            FROM outbound_delivery_items odi
            WHERE odi.plant IS NOT NULL
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'delivery_item_billed_by_billing_item_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0')
                    || '_' || bdi.billingdocument || '_' || lpad(CAST(bdi.billingdocumentitem AS VARCHAR), 6, '0') AS edge_id,
                'deliveryitem_' || odi.deliverydocument || '_' || lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0') AS source_id,
                'billingitem_' || bdi.billingdocument || '_' || lpad(CAST(bdi.billingdocumentitem AS VARCHAR), 6, '0') AS target_id,
                'DELIVERY_ITEM_BILLED_BY_BILLING_ITEM' AS edge_type,
                json_object(
                    'billing_document', bdi.billingdocument,
                    'billed_quantity', bdi.billingquantity
                ) AS metadata_json
            FROM outbound_delivery_items odi
            JOIN billing_document_items bdi
              ON odi.deliverydocument = bdi.referencesddocument
             AND lpad(CAST(odi.deliverydocumentitem AS VARCHAR), 6, '0')
                 = lpad(CAST(bdi.referencesddocumentitem AS VARCHAR), 6, '0')
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'billing_item_in_document_' || bdi.billingdocument || '_' || lpad(CAST(bdi.billingdocumentitem AS VARCHAR), 6, '0') AS edge_id,
                'billingitem_' || bdi.billingdocument || '_' || lpad(CAST(bdi.billingdocumentitem AS VARCHAR), 6, '0') AS source_id,
                'billingdocument_' || bdi.billingdocument AS target_id,
                'BILLING_ITEM_IN_DOCUMENT' AS edge_type,
                json_object('relationship', 'parent_child') AS metadata_json
            FROM billing_document_items bdi
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'billing_document_posted_to_journal_entry_' || bdh.billingdocument || '_' || je.accountingdocument || '_' || CAST(je.accountingdocumentitem AS VARCHAR) AS edge_id,
                'billingdocument_' || bdh.billingdocument AS source_id,
                'journalentry_' || je.accountingdocument || '_' || CAST(je.accountingdocumentitem AS VARCHAR) AS target_id,
                'BILLING_DOCUMENT_POSTED_TO_JOURNAL_ENTRY' AS edge_type,
                json_object(
                    'accounting_document', je.accountingdocument,
                    'posted_amount', je.amountintransactioncurrency
                ) AS metadata_json
            FROM billing_document_headers bdh
            JOIN journal_entry_items_accounts_receivable je
              ON bdh.accountingdocument = je.accountingdocument
            WHERE bdh.accountingdocument IS NOT NULL
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'customer_has_address_' || bpa.businessPartner || '_' || bpa.addressId AS edge_id,
                'customer_' || bpa.businessPartner AS source_id,
                'address_' || bpa.businessPartner || '_' || bpa.addressId AS target_id,
                'CUSTOMER_HAS_ADDRESS' AS edge_type,
                json_object('address_id', bpa.addressId) AS metadata_json
            FROM business_partner_addresses bpa
            JOIN business_partners bp
              ON bpa.businessPartner = bp.businessPartner
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'billing_document_for_customer_' || bdh.billingdocument AS edge_id,
                'billingdocument_' || bdh.billingdocument AS source_id,
                'customer_' || bdh.soldtoparty AS target_id,
                'BILLING_DOCUMENT_FOR_CUSTOMER' AS edge_type,
                json_object('customer', bdh.soldtoparty) AS metadata_json
            FROM billing_document_headers bdh
            WHERE bdh.soldtoparty IS NOT NULL
            """
        )

        self.conn.execute(
            """
            INSERT INTO graph_edges (edge_id, source_id, target_id, edge_type, metadata_json)
            SELECT DISTINCT
                'payment_clears_journal_entry_' || par.accountingdocument || '_' || je.accountingdocument || '_' || CAST(je.accountingdocumentitem AS VARCHAR) AS edge_id,
                'payment_' || par.accountingdocument AS source_id,
                'journalentry_' || je.accountingdocument || '_' || CAST(je.accountingdocumentitem AS VARCHAR) AS target_id,
                'PAYMENT_CLEARS_JOURNAL_ENTRY' AS edge_type,
                json_object(
                    'cleared_document', par.clearingaccountingdocument,
                    'clearing_date', par.clearingdate
                ) AS metadata_json
            FROM payments_accounts_receivable par
            JOIN journal_entry_items_accounts_receivable je
              ON par.clearingaccountingdocument = je.accountingdocument
            WHERE par.clearingaccountingdocument IS NOT NULL
            """
        )

        self.conn.commit()
        result = self.conn.execute("SELECT COUNT(*) FROM graph_edges").fetchone()
        return int(result[0]) if result else 0

    def get_node_details(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific node."""
        row = self.conn.execute(
            """
            SELECT node_id, node_type, label, metadata_json
            FROM graph_nodes
            WHERE node_id = ?
            """,
            [node_id],
        ).fetchone()

        if not row:
            return None

        return {
            "node_id": row[0],
            "node_type": row[1],
            "label": row[2],
            "metadata": self._parse_json(row[3]),
        }

    def get_subgraph(self, node_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """Get subgraph centered on a node."""
        max_depth = max(1, min(max_depth, 2))

        center = self.get_node_details(node_id)
        if not center:
            return {"nodes": [], "edges": []}

        nodes: Dict[str, Dict[str, Any]] = {node_id: center}
        edges: Dict[str, Dict[str, Any]] = {}

        frontier = {node_id}
        visited = {node_id}

        for _ in range(max_depth):
            if not frontier:
                break

            placeholders = ",".join(["?"] * len(frontier))
            query = f"""
                SELECT edge_id, source_id, target_id, edge_type, metadata_json
                FROM graph_edges
                WHERE source_id IN ({placeholders}) OR target_id IN ({placeholders})
            """
            rows = self.conn.execute(query, list(frontier) + list(frontier)).fetchall()

            next_frontier = set()
            for row in rows:
                edge_id, source_id, target_id, edge_type, metadata_json = row
                edges[edge_id] = {
                    "edge_id": edge_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "edge_type": edge_type,
                    "metadata": self._parse_json(metadata_json),
                }

                for neighbor_id in (source_id, target_id):
                    if neighbor_id not in nodes:
                        node = self.get_node_details(neighbor_id)
                        if node:
                            nodes[neighbor_id] = node
                    if neighbor_id not in visited:
                        next_frontier.add(neighbor_id)

            visited.update(next_frontier)
            frontier = next_frontier

        return {
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
        }

    def get_graph_overview(self) -> Dict[str, Any]:
        """Get overview statistics of the graph."""
        node_counts = self.get_node_counts()
        edge_counts = self.get_edge_counts()

        return {
            "node_counts": node_counts,
            "edge_counts": edge_counts,
            "total_nodes": sum(node_counts.values()),
            "total_edges": sum(edge_counts.values()),
            "sample_nodes": self.get_sample_nodes(),
            "sample_edges": self.get_sample_edges(),
        }

    def get_node_counts(self) -> Dict[str, int]:
        """Get count of nodes by type."""
        try:
            rows = self.conn.execute(
                """
                SELECT node_type, COUNT(*) AS count
                FROM graph_nodes
                GROUP BY node_type
                ORDER BY count DESC
                """
            ).fetchall()
            return {row[0]: int(row[1]) for row in rows}
        except Exception:
            return {}

    def get_edge_counts(self) -> Dict[str, int]:
        """Get count of edges by type."""
        try:
            rows = self.conn.execute(
                """
                SELECT edge_type, COUNT(*) AS count
                FROM graph_edges
                GROUP BY edge_type
                ORDER BY count DESC
                """
            ).fetchall()
            return {row[0]: int(row[1]) for row in rows}
        except Exception:
            return {}

    def get_sample_nodes(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample nodes."""
        try:
            rows = self.conn.execute(
                """
                SELECT node_id, node_type, label, metadata_json
                FROM graph_nodes
                ORDER BY node_type, node_id
                LIMIT ?
                """,
                [limit],
            ).fetchall()

            return [
                {
                    "node_id": row[0],
                    "node_type": row[1],
                    "label": row[2],
                    "metadata": self._parse_json(row[3]),
                }
                for row in rows
            ]
        except Exception:
            return []

    def get_sample_edges(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get sample edges."""
        try:
            rows = self.conn.execute(
                """
                SELECT edge_id, source_id, target_id, edge_type, metadata_json
                FROM graph_edges
                ORDER BY edge_type, edge_id
                LIMIT ?
                """,
                [limit],
            ).fetchall()

            return [
                {
                    "edge_id": row[0],
                    "source_id": row[1],
                    "target_id": row[2],
                    "edge_type": row[3],
                    "metadata": self._parse_json(row[4]),
                }
                for row in rows
            ]
        except Exception:
            return []

    def get_node_with_neighbors(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node with its direct neighbors."""
        node = self.get_node_details(node_id)
        if not node:
            return None

        rows = self.conn.execute(
            """
            SELECT edge_id, source_id, target_id, edge_type, metadata_json
            FROM graph_edges
            WHERE source_id = ? OR target_id = ?
            """,
            [node_id, node_id],
        ).fetchall()

        incoming_edges: List[Dict[str, Any]] = []
        outgoing_edges: List[Dict[str, Any]] = []
        neighbor_ids = set()

        for row in rows:
            edge = {
                "edge_id": row[0],
                "source_id": row[1],
                "target_id": row[2],
                "edge_type": row[3],
                "metadata": self._parse_json(row[4]),
            }

            if row[2] == node_id:
                incoming_edges.append(edge)
                neighbor_ids.add(row[1])
            if row[1] == node_id:
                outgoing_edges.append(edge)
                neighbor_ids.add(row[2])

        neighbors = [self.get_node_details(neighbor_id) for neighbor_id in neighbor_ids]
        neighbors = [neighbor for neighbor in neighbors if neighbor is not None]

        return {
            "node": node,
            "incoming_edges": incoming_edges,
            "outgoing_edges": outgoing_edges,
            "neighbors": neighbors,
        }