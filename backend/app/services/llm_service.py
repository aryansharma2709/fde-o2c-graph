"""LLM service with optional provider abstraction."""

import os
from typing import Optional


class LLMService:
    """LLM abstraction layer with optional API key fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.provider = "openai" if os.getenv("OPENAI_API_KEY") else "anthropic" if os.getenv("ANTHROPIC_API_KEY") else None
        self.available = bool(self.api_key and self.provider)

    def classify_intent(self, prompt: str) -> Optional[str]:
        """
        Classify intent using LLM if available, otherwise return None.
        Intents: top_products, broken_flows, trace_billing_flow, graph_explore, unknown
        """
        if not self.available:
            return None

        try:
            # Placeholder for actual LLM call
            # In production, would call OpenAI or Anthropic API
            # For now, return None to force deterministic routing
            return None
        except Exception as e:
            print(f"LLM classification failed: {e}")
            return None

    def rephrase_response(self, data_summary: str, original_prompt: str) -> Optional[str]:
        """
        Use LLM to rephrase data summary into natural language.
        If not available, return None and caller uses raw data_summary.
        """
        if not self.available:
            return None

        try:
            # Placeholder for actual LLM call
            # In production, would refine response text
            return None
        except Exception as e:
            print(f"LLM rephrase failed: {e}")
            return None
