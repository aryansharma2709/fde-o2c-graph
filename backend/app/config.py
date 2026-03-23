"""Configuration settings for the O2C Graph Explorer backend."""

import os
from pathlib import Path


class Config:
    """Application configuration."""

    # Project root
    PROJECT_ROOT = Path(__file__).parent.parent.parent

    # Data paths
    DATA_DIR = PROJECT_ROOT / "data"
    RAW_DATA_DIR = DATA_DIR / "raw" / "sap-o2c-data" / "sap-o2c-data"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"

    # Database
    DATABASE_PATH = PROCESSED_DATA_DIR / "o2c_graph.db"

    # Ensure directories exist
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Collection names (from dataset audit)
    COLLECTIONS = [
        "sales_order_headers",
        "sales_order_items",
        "outbound_delivery_headers",
        "outbound_delivery_items",
        "billing_document_headers",
        "billing_document_items",
        "billing_document_cancellations",
        "journal_entry_items_accounts_receivable",
        "payments_accounts_receivable",
        "business_partners",
        "business_partner_addresses",
        "products",
        "product_descriptions",
        "plants",
        "product_plants",
        "product_storage_locations",
        "customer_company_assignments",
        "customer_sales_area_assignments",
        "sales_order_schedule_lines",
    ]

    # Node types
    NODE_TYPES = [
        "Customer",
        "Address",
        "SalesOrder",
        "SalesOrderItem",
        "Product",
        "Delivery",
        "DeliveryItem",
        "Plant",
        "BillingDocument",
        "BillingItem",
        "JournalEntry",
        "Payment",
    ]

    # Edge types
    EDGE_TYPES = [
        "CUSTOMER_PLACED_ORDER",
        "ORDER_HAS_ITEM",
        "ITEM_FOR_PRODUCT",
        "ITEM_FULFILLED_BY_DELIVERY_ITEM",
        "DELIVERY_ITEM_IN_DELIVERY",
        "DELIVERY_ITEM_FROM_PLANT",
        "DELIVERY_ITEM_BILLED_BY_BILLING_ITEM",
        "BILLING_ITEM_IN_DOCUMENT",
        "BILLING_DOCUMENT_POSTED_TO_JOURNAL_ENTRY",
        "CUSTOMER_HAS_ADDRESS",
        "BILLING_DOCUMENT_FOR_CUSTOMER",
        "PAYMENT_CLEARS_JOURNAL_ENTRY",
    ]


# Export settings instance
settings = Config()