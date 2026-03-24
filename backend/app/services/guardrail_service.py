"""Guardrail service for domain validation without LLM dependency."""

import re
from typing import Tuple


class GuardrailService:
    """Deterministic out-of-domain detection."""

    # In-domain keywords
    IN_DOMAIN_KEYWORDS = {
        # Products
        "product", "products", "material", "materials", "sku", "billing",
        # Flows
        "flow", "flows", "broken", "incomplete", "missing", "delivered", "billed",
        "delivery", "invoice", "document", "documents", "order", "orders",
        # Business metrics
        "count", "sales", "order", "billing", "payment", "document", "trace",
        # Data exploration
        "which", "what", "show", "list", "rank", "highest", "lowest", "top",
        # O2C specific
        "sales_order", "billing_document", "outbound_delivery", "journal_entry",
        "accounts_receivable", "outstanding", "overdue", "reconcile", "ledger",
        # Common variations
        "downstream", "upstream", "lineage", "trace", "path", "connection",
    }

    OUT_OF_DOMAIN_KEYWORDS = {
        # Weather
        "weather", "temperature", "rain", "sunny", "cloud", "forecast",
        # Sports
        "score", "game", "team", "player", "championship", "league", "match",
        # News
        "news", "headline", "breaking", "election", "war", "president",
        # Entertainment
        "movie", "music", "actor", "singer", "episode", "season",
        # General knowledge
        "capital", "population", "history", "author", "book", "poem",
        # Personal
        "how are you", "what time", "what date", "joke", "funny", "laugh",
        # Tech unrelated to data
        "api", "rest", "function", "code", "programming", "python", "javascript",
        # Other domains
        "stock", "crypto", "forex", "investment", "portfolio", "dividend",
    }

    @staticmethod
    def normalize_prompt(text: str) -> str:
        """Normalize prompt to lowercase alphanumeric + spaces."""
        return re.sub(r"[^\w\s]", " ", text.lower()).strip()

    @classmethod
    def is_in_domain(cls, prompt: str) -> Tuple[bool, str]:
        """
        Determine if prompt is in-domain (SAP O2C dataset).
        Returns (is_in_domain, reason).
        """
        normalized = cls.normalize_prompt(prompt)
        words = set(normalized.split())

        # Check if explicitly out-of-domain
        out_of_domain_matches = words & cls.OUT_OF_DOMAIN_KEYWORDS
        if out_of_domain_matches:
            return False, f"Query contains out-of-domain keywords: {', '.join(sorted(out_of_domain_matches)[:3])}"

        # Check if explicitly in-domain
        in_domain_matches = words & cls.IN_DOMAIN_KEYWORDS
        if in_domain_matches:
            return True, "Query contains in-domain keywords"

        # If neutral/ambiguous, default to out-of-domain to be conservative
        if len(words) > 0:
            return False, "Query does not match known in-domain patterns"

        return False, "Empty query"

    @classmethod
    def is_out_of_domain(cls, prompt: str) -> bool:
        """Simple check: return True if out-of-domain."""
        is_in, _ = cls.is_in_domain(prompt)
        return not is_in
