"""
Graph service for building and querying graph projections from SAP O2C data.
"""

import json
from typing import Dict, List, Any, Optional
from ..db.connection import get_db_connection
from ..config import settings


class GraphService:
    """Service for graph operations on SAP O2C data."""

    def __init__(self):
        self.conn = get_db_connection()

    def build_graph_nodes(self) -> None:
        """Build graph nodes from relational tables."""
        with self.conn.cursor() as cur:
            # Clear existing nodes
            cur.execute("DELETE FROM graph_nodes")

            # Insert Order nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'order_' || order_id as node_id,
                    'Order' as node_type,
                    json_object(
                        'order_id', order_id,
                        'order_type', order_type,
                        'order_date', order_date,
                        'supplier_id', supplier_id,
                        'plant_id', plant_id,
                        'total_amount', total_amount,
                        'currency', currency
                    ) as properties
                FROM orders
            """)

            # Insert OrderItem nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'orderitem_' || order_id || '_' || item_id as node_id,
                    'OrderItem' as node_type,
                    json_object(
                        'order_id', order_id,
                        'item_id', item_id,
                        'material_id', material_id,
                        'quantity', quantity,
                        'unit', unit,
                        'unit_price', unit_price,
                        'total_price', total_price,
                        'currency', currency,
                        'delivery_date', delivery_date
                    ) as properties
                FROM order_items
            """)

            # Insert Fulfillment nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'fulfillment_' || fulfillment_id as node_id,
                    'Fulfillment' as node_type,
                    json_object(
                        'fulfillment_id', fulfillment_id,
                        'order_id', order_id,
                        'item_id', item_id,
                        'fulfilled_quantity', fulfilled_quantity,
                        'fulfillment_date', fulfillment_date,
                        'status', status
                    ) as properties
                FROM fulfillments
            """)

            # Insert Invoice nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'invoice_' || invoice_id as node_id,
                    'Invoice' as node_type,
                    json_object(
                        'invoice_id', invoice_id,
                        'order_id', order_id,
                        'item_id', item_id,
                        'invoice_amount', invoice_amount,
                        'invoice_date', invoice_date,
                        'due_date', due_date,
                        'currency', currency,
                        'status', status
                    ) as properties
                FROM invoices
            """)

            # Insert Payment nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'payment_' || payment_id as node_id,
                    'Payment' as node_type,
                    json_object(
                        'payment_id', payment_id,
                        'invoice_id', invoice_id,
                        'payment_amount', payment_amount,
                        'payment_date', payment_date,
                        'payment_method', payment_method,
                        'currency', currency,
                        'status', status
                    ) as properties
                FROM payments
            """)

            # Insert Supplier nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'supplier_' || supplier_id as node_id,
                    'Supplier' as node_type,
                    json_object(
                        'supplier_id', supplier_id,
                        'supplier_name', supplier_name,
                        'supplier_type', supplier_type,
                        'country', country,
                        'region', region
                    ) as properties
                FROM suppliers
            """)

            # Insert Material nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'material_' || material_id as node_id,
                    'Material' as node_type,
                    json_object(
                        'material_id', material_id,
                        'material_name', material_name,
                        'material_type', material_type,
                        'unit_of_measure', unit_of_measure,
                        'material_group', material_group
                    ) as properties
                FROM materials
            """)

            # Insert Plant nodes
            cur.execute("""
                INSERT INTO graph_nodes (node_id, node_type, properties)
                SELECT
                    'plant_' || plant_id as node_id,
                    'Plant' as node_type,
                    json_object(
                        'plant_id', plant_id,
                        'plant_name', plant_name,
                        'location', location,
                        'plant_type', plant_type
                    ) as properties
                FROM plants
            """)

        self.conn.commit()

    def build_graph_edges(self) -> None:
        """Build graph edges from relational relationships."""
        with self.conn.cursor() as cur:
            # Clear existing edges
            cur.execute("DELETE FROM graph_edges")

            # Order -> OrderItem (INCLUDES)
            cur.execute("""
                INSERT INTO graph_edges (edge_id, source_node_id, target_node_id, edge_type, properties)
                SELECT
                    'includes_' || o.order_id || '_' || oi.item_id as edge_id,
                    'order_' || o.order_id as source_node_id,
                    'orderitem_' || oi.order_id || '_' || oi.item_id as target_node_id,
                    'INCLUDES' as edge_type,
                    json_object('relationship', 'parent_child') as properties
                FROM orders o
                JOIN order_items oi ON o.order_id = oi.order_id
            """)

            # OrderItem -> Fulfillment (FULFILLED_BY)
            cur.execute("""
                INSERT INTO graph_edges (edge_id, source_node_id, target_node_id, edge_type, properties)
                SELECT
                    'fulfilled_by_' || oi.order_id || '_' || oi.item_id || '_' || f.fulfillment_id as edge_id,
                    'orderitem_' || oi.order_id || '_' || oi.item_id as source_node_id,
                    'fulfillment_' || f.fulfillment_id as target_node_id,
                    'FULFILLED_BY' as edge_type,
                    json_object('fulfilled_quantity', f.fulfilled_quantity) as properties
                FROM order_items oi
                JOIN fulfillments f ON oi.order_id = f.order_id AND oi.item_id = f.item_id
            """)

            # OrderItem -> Invoice (INVOICED_IN)
            cur.execute("""
                INSERT INTO graph_edges (edge_id, source_node_id, target_node_id, edge_type, properties)
                SELECT
                    'invoiced_in_' || oi.order_id || '_' || oi.item_id || '_' || i.invoice_id as edge_id,
                    'orderitem_' || oi.order_id || '_' || oi.item_id as source_node_id,
                    'invoice_' || i.invoice_id as target_node_id,
                    'INVOICED_IN' as edge_type,
                    json_object('invoice_amount', i.invoice_amount) as properties
                FROM order_items oi
                JOIN invoices i ON oi.order_id = i.order_id AND oi.item_id = i.item_id
            """)

            # Invoice -> Payment (PAID_BY)
            cur.execute("""
                INSERT INTO graph_edges (edge_id, source_node_id, target_node_id, edge_type, properties)
                SELECT
                    'paid_by_' || i.invoice_id || '_' || p.payment_id as edge_id,
                    'invoice_' || i.invoice_id as source_node_id,
                    'payment_' || p.payment_id as target_node_id,
                    'PAID_BY' as edge_type,
                    json_object('payment_amount', p.payment_amount) as properties
                FROM invoices i
                JOIN payments p ON i.invoice_id = p.invoice_id
            """)

            # Order -> Supplier (SUPPLIED_BY)
            cur.execute("""
                INSERT INTO graph_edges (edge_id, source_node_id, target_node_id, edge_type, properties)
                SELECT
                    'supplied_by_' || o.order_id || '_' || s.supplier_id as edge_id,
                    'order_' || o.order_id as source_node_id,
                    'supplier_' || s.supplier_id as target_node_id,
                    'SUPPLIED_BY' as edge_type,
                    json_object('relationship', 'business_partner') as properties
                FROM orders o
                JOIN suppliers s ON o.supplier_id = s.supplier_id
            """)

            # OrderItem -> Material (IS_MATERIAL)
            cur.execute("""
                INSERT INTO graph_edges (edge_id, source_node_id, target_node_id, edge_type, properties)
                SELECT
                    'is_material_' || oi.order_id || '_' || oi.item_id || '_' || m.material_id as edge_id,
                    'orderitem_' || oi.order_id || '_' || oi.item_id as source_node_id,
                    'material_' || m.material_id as target_node_id,
                    'IS_MATERIAL' as edge_type,
                    json_object('quantity', oi.quantity, 'unit', oi.unit) as properties
                FROM order_items oi
                JOIN materials m ON oi.material_id = m.material_id
            """)

            # Order -> Plant (RECEIVED_AT)
            cur.execute("""
                INSERT INTO graph_edges (edge_id, source_node_id, target_node_id, edge_type, properties)
                SELECT
                    'received_at_' || o.order_id || '_' || p.plant_id as edge_id,
                    'order_' || o.order_id as source_node_id,
                    'plant_' || p.plant_id as target_node_id,
                    'RECEIVED_AT' as edge_type,
                    json_object('relationship', 'delivery_location') as properties
                FROM orders o
                JOIN plants p ON o.plant_id = p.plant_id
            """)

        self.conn.commit()

    def get_node_details(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific node."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT node_id, node_type, properties
                FROM graph_nodes
                WHERE node_id = ?
            """, (node_id,))

            row = cur.fetchone()
            if row:
                return {
                    "node_id": row[0],
                    "node_type": row[1],
                    "properties": json.loads(row[2]) if row[2] else {}
                }
            return None

    def get_subgraph(self, node_id: str, max_depth: int = 2) -> Dict[str, Any]:
        """Get subgraph centered on a node with relationships."""
        nodes = {}
        edges = []

        # Get the central node
        central_node = self.get_node_details(node_id)
        if not central_node:
            return {"nodes": [], "edges": []}

        nodes[node_id] = central_node

        # Get directly connected nodes and edges
        with self.conn.cursor() as cur:
            # Outgoing edges
            cur.execute("""
                SELECT e.edge_id, e.source_node_id, e.target_node_id, e.edge_type, e.properties,
                       n.node_id, n.node_type, n.properties
                FROM graph_edges e
                JOIN graph_nodes n ON e.target_node_id = n.node_id
                WHERE e.source_node_id = ?
            """, (node_id,))

            for row in cur.fetchall():
                edge_id, source_id, target_id, edge_type, edge_props, node_id2, node_type, node_props = row
                edges.append({
                    "edge_id": edge_id,
                    "source_node_id": source_id,
                    "target_node_id": target_id,
                    "edge_type": edge_type,
                    "properties": json.loads(edge_props) if edge_props else {}
                })
                nodes[target_id] = {
                    "node_id": node_id2,
                    "node_type": node_type,
                    "properties": json.loads(node_props) if node_props else {}
                }

            # Incoming edges
            cur.execute("""
                SELECT e.edge_id, e.source_node_id, e.target_node_id, e.edge_type, e.properties,
                       n.node_id, n.node_type, n.properties
                FROM graph_edges e
                JOIN graph_nodes n ON e.source_node_id = n.node_id
                WHERE e.target_node_id = ?
            """, (node_id,))

            for row in cur.fetchall():
                edge_id, source_id, target_id, edge_type, edge_props, node_id2, node_type, node_props = row
                edges.append({
                    "edge_id": edge_id,
                    "source_node_id": source_id,
                    "target_node_id": target_id,
                    "edge_type": edge_type,
                    "properties": json.loads(edge_props) if edge_props else {}
                })
                nodes[source_id] = {
                    "node_id": node_id2,
                    "node_type": node_type,
                    "properties": json.loads(node_props) if node_props else {}
                }

        return {
            "nodes": list(nodes.values()),
            "edges": edges
        }

    def get_graph_overview(self) -> Dict[str, Any]:
        """Get overview statistics of the graph."""
        with self.conn.cursor() as cur:
            # Node counts by type
            cur.execute("""
                SELECT node_type, COUNT(*) as count
                FROM graph_nodes
                GROUP BY node_type
                ORDER BY count DESC
            """)

            node_counts = {row[0]: row[1] for row in cur.fetchall()}

            # Edge counts by type
            cur.execute("""
                SELECT edge_type, COUNT(*) as count
                FROM graph_edges
                GROUP BY edge_type
                ORDER BY count DESC
            """)

            edge_counts = {row[0]: row[1] for row in cur.fetchall()}

            return {
                "node_counts": node_counts,
                "edge_counts": edge_counts,
                "total_nodes": sum(node_counts.values()),
                "total_edges": sum(edge_counts.values())
            }