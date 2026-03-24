"""Chat service for natural language queries routed to deterministic backends."""

import re
from typing import Any, Dict, List, Optional, Tuple

from .guardrail_service import GuardrailService
from .llm_service import LLMService
from .query_service import QueryService


class ChatService:
    """Route NL prompts to deterministic query backends with guardrails."""

    def __init__(self) -> None:
        self.query_service = QueryService()
        self.guardrail_service = GuardrailService()
        self.llm_service = LLMService()

    def chat(self, prompt: str) -> Dict[str, Any]:
        """Process a user prompt and return grounded response."""
        if not prompt or not prompt.strip():
            return self._empty_prompt_response()

        # Step 1: Guardrail check
        if self.guardrail_service.is_out_of_domain(prompt):
            return self._out_of_domain_response(prompt)

        # Step 2: Intent classification
        intent, extracted_data = self._classify_intent_and_extract(prompt)

        # Step 3: Route to appropriate backend
        if intent == "top_products":
            return self._handle_top_products(prompt, extracted_data)
        elif intent == "broken_flows":
            return self._handle_broken_flows(prompt, extracted_data)
        elif intent == "trace_billing_flow":
            return self._handle_trace_billing_flow(prompt, extracted_data)
        elif intent == "graph_explore":
            return self._handle_graph_explore(prompt, extracted_data)
        else:
            return self._clarify_intent_response(prompt)

    def _classify_intent_and_extract(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Deterministic intent classification with data extraction."""
        prompt_lower = prompt.lower()
        extracted: Dict[str, Any] = {}

        # Extract billing document ID if present (e.g., "90504248", "billing doc 90504248")
        billing_id_match = re.search(r"\b(\d{8,})\b", prompt)
        if billing_id_match:
            extracted["billing_document_id"] = billing_id_match.group(1)

        # Extract limit if present
        limit_match = re.search(r"(?:top|highest|first)\s+(\d+)", prompt_lower)
        if limit_match:
            extracted["limit"] = int(limit_match.group(1))

        # Intent patterns (deterministic first)
        if any(phrase in prompt_lower for phrase in [
            "top product", "highest billing", "most billing",
            "which product", "products by billing",
        ]):
            return "top_products", extracted

        if any(phrase in prompt_lower for phrase in [
            "broken flow", "incomplete flow", "delivered not billed",
            "billed without delivery", "no downstream", "broken",
            "missing flow", "incomplete", "show broken", "broken flows",
            "incomplete flows", "show incomplete", "sales orders no downstream",
            "which sales orders have no downstream", "delivered but not billed",
            "billed without delivery", "show incomplete orders"
        ]):
            return "broken_flows", extracted

        if any(phrase in prompt_lower for phrase in [
            "trace billing", "trace document", "billing flow",
            "trace " + str(extracted.get("billing_document_id", "")),
        ]):
            if extracted.get("billing_document_id"):
                return "trace_billing_flow", extracted
            else:
                return "trace_billing_flow", {"needs_clarification": True}

        if any(phrase in prompt_lower for phrase in [
            "explore", "show", "graph", "relationships", "connected"
        ]):
            return "graph_explore", extracted

        # Unknown
        return "unknown", extracted

    def _handle_top_products(self, prompt: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Route to top-products query."""
        try:
            limit = extracted.get("limit", 10)
            result = self.query_service.top_products_by_billing_count(limit=limit)

            products = result.get("results", [])
            if not products:
                answer_text = "No products found in the dataset."
                cited_data = {"count": 0}
            else:
                top_product = products[0]
                answer_text = (
                    f"The top product is '{top_product['product']}' "
                    f"with {top_product['billing_document_count']} billing documents. "
                    f"Here are the top {len(products)} products by billing document count."
                )
                cited_data = result

            referenced_node_ids = [p["product"] for p in products[:10]]

            return {
                "answer_text": answer_text,
                "intent": "top_products",
                "cited_data_summary": cited_data,
                "referenced_node_ids": referenced_node_ids,
                "referenced_edge_ids": [],
                "requires_clarification": False,
            }
        except Exception as e:
            return self._error_response(f"top_products query failed: {e}")

    def _handle_broken_flows(self, prompt: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Route to broken-flows query."""
        try:
            result = self.query_service.broken_flows()

            delivered_not_billed = result.get("delivered_but_not_billed", {})
            billed_without_delivery = result.get("billed_without_delivery", {})
            sales_orders_no_flow = result.get("sales_orders_with_no_downstream_flow", {})

            total_broken = (
                delivered_not_billed.get("count", 0)
                + billed_without_delivery.get("count", 0)
                + sales_orders_no_flow.get("count", 0)
            )

            answer_text = (
                f"Found {total_broken} broken flows in the O2C process:\n"
                f"- {delivered_not_billed.get('count', 0)} deliveries not billed\n"
                f"- {billed_without_delivery.get('count', 0)} billing docs without delivery\n"
                f"- {sales_orders_no_flow.get('count', 0)} sales orders with no downstream flow"
            )

            referenced_node_ids = (
                delivered_not_billed.get("sample_ids", [])
                + billed_without_delivery.get("sample_ids", [])
                + sales_orders_no_flow.get("sample_ids", [])
            )[:50]

            return {
                "answer_text": answer_text,
                "intent": "broken_flows",
                "cited_data_summary": result,
                "referenced_node_ids": referenced_node_ids,
                "referenced_edge_ids": [],
                "requires_clarification": False,
            }
        except Exception as e:
            return self._error_response(f"broken_flows query failed: {e}")

    def _handle_trace_billing_flow(self, prompt: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Route to trace-billing-flow query."""
        if extracted.get("needs_clarification"):
            return {
                "answer_text": "Which billing document would you like me to trace? Please provide a billing document ID.",
                "intent": "trace_billing_flow",
                "cited_data_summary": {},
                "referenced_node_ids": [],
                "referenced_edge_ids": [],
                "requires_clarification": True,
            }

        billing_document_id = extracted.get("billing_document_id")
        if not billing_document_id:
            return {
                "answer_text": "Please provide a billing document ID to trace (e.g., '90504248').",
                "intent": "trace_billing_flow",
                "cited_data_summary": {},
                "referenced_node_ids": [],
                "referenced_edge_ids": [],
                "requires_clarification": True,
            }

        try:
            result = self.query_service.trace_billing_flow(billing_document_id)

            if "error" in result:
                return {
                    "answer_text": result["error"],
                    "intent": "trace_billing_flow",
                    "cited_data_summary": {},
                    "referenced_node_ids": [],
                    "referenced_edge_ids": [],
                    "requires_clarification": False,
                }

            summary = result.get("summary", {})
            nodes = result.get("nodes", [])
            edges = result.get("edges", [])

            # Extract data from nodes and edges lists
            customer = None
            billing_items_count = 0
            delivery_items_count = 0
            sales_order_items_count = 0
            journal_entry_count = 0

            node_ids = []
            for node in nodes:
                if isinstance(node, dict):
                    node_id = node.get("node_id") or node.get("id")
                    if node_id:
                        node_ids.append(node_id)
                    
                    node_type = node.get("node_type")
                    if node_type == "Customer":
                        customer = node.get("label") or node_id
                    elif node_type == "BillingItem":
                        billing_items_count += 1
                    elif node_type == "DeliveryItem":
                        delivery_items_count += 1
                    elif node_type == "SalesOrderItem":
                        sales_order_items_count += 1
                    elif node_type == "JournalEntry":
                        journal_entry_count += 1

            edge_ids = [edge.get("edge_id") for edge in edges if isinstance(edge, dict) and edge.get("edge_id")]

            answer_text = (
                f"Traced billing document {billing_document_id}:\n"
                f"- Customer: {customer or 'N/A'}\n"
                f"- Billing Items: {billing_items_count}\n"
                f"- Delivery Items: {delivery_items_count}\n"
                f"- Sales Order Items: {sales_order_items_count}\n"
                f"- Posted to Journal Entry: {'Yes' if journal_entry_count > 0 else 'No'}"
            )

            return {
                "answer_text": answer_text,
                "intent": "trace_billing_flow",
                "cited_data_summary": summary,
                "referenced_node_ids": node_ids,
                "referenced_edge_ids": edge_ids,
                "requires_clarification": False,
            }
        except Exception as e:
            return self._error_response(f"trace query failed: {e}")

    def _handle_graph_explore(self, prompt: str, extracted: Dict[str, Any]) -> Dict[str, Any]:
        """Handle graph exploration prompts."""
        return {
            "answer_text": "Graph exploration queries are not yet supported. Try asking about top products, broken flows, or trace a billing document.",
            "intent": "graph_explore",
            "cited_data_summary": {},
            "referenced_node_ids": [],
            "referenced_edge_ids": [],
            "requires_clarification": True,
        }

    def _out_of_domain_response(self, prompt: str) -> Dict[str, Any]:
        """Return guardrail rejection."""
        return {
            "answer_text": "This system is designed to answer questions related to the provided dataset only.",
            "intent": "out_of_domain",
            "cited_data_summary": {},
            "referenced_node_ids": [],
            "referenced_edge_ids": [],
            "requires_clarification": False,
        }

    def _clarify_intent_response(self, prompt: str) -> Dict[str, Any]:
        """Ask for clarification."""
        return {
            "answer_text": (
                "I'm not sure what you're asking. Try asking about:\n"
                "- Top products by billing document count\n"
                "- Broken flows in the O2C process\n"
                "- Trace a specific billing document (e.g., '90504248')"
            ),
            "intent": "unknown",
            "cited_data_summary": {},
            "referenced_node_ids": [],
            "referenced_edge_ids": [],
            "requires_clarification": True,
        }

    def _empty_prompt_response(self) -> Dict[str, Any]:
        """Handle empty prompt."""
        return {
            "answer_text": "Please provide a question or query.",
            "intent": "unknown",
            "cited_data_summary": {},
            "referenced_node_ids": [],
            "referenced_edge_ids": [],
            "requires_clarification": True,
        }

    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Handle errors gracefully."""
        return {
            "answer_text": f"An error occurred processing your query: {error_msg}",
            "intent": "error",
            "cited_data_summary": {},
            "referenced_node_ids": [],
            "referenced_edge_ids": [],
            "requires_clarification": False,
        }
