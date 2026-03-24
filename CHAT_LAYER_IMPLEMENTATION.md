# Chat Layer Implementation Summary

## Overview
Natural language chat layer has been implemented on top of the existing deterministic backend query engine. The system routes user prompts through guardrails, intent classification, and deterministic backend calls, returning grounded responses with referenced node/edge IDs.

## Architecture

```
User Prompt
    ↓
[Guardrail Check] ← GuardrailService (keyword-based, no LLM required)
    ↓ (if in-domain)
[Intent Classification] ← ChatService (deterministic patterns first)
    ↓
[Route to Backend] ← QueryService (existing deterministic endpoints)
    ↓
[Synthesize Response] ← ChatService (format data + reference IDs)
    ↓
JSON Response (answer_text, intent, cited_data, node_ids, edge_ids)
```

## Files Changed

### New Files Created:
1. **backend/app/services/guardrail_service.py**
   - Out-of-domain detection using keyword matching
   - No LLM dependency
   - Returns: (is_in_domain: bool, reason: str)

2. **backend/app/services/llm_service.py**
   - Optional LLM abstraction (currently stub)
   - Checks for OPENAI_API_KEY or ANTHROPIC_API_KEY env vars
   - Falls back gracefully if not configured
   - Placeholder methods for future enhancement

3. **backend/app/services/chat_service.py**
   - Main orchestration layer
   - Deterministic intent routing with pattern matching
   - Routes to: top_products, broken_flows, trace_billing_flow, graph_explore
   - Handles clarification requests when data is missing
   - Extracts billing document IDs and limits from prompts

4. **backend/app/routers/chat.py**
   - POST /api/chat endpoint
   - Expects: {"prompt": "user query string"}
   - Returns: structured ChatResponse with all metadata

### Modified Files:
1. **backend/app/schemas.py**
   - Added ChatRequest schema
   - Added ChatResponse schema with grounded response fields

2. **backend/app/main.py**
   - Imported chat_router
   - Registered chat_router with app

## Supported Intent Classes

| Intent | Trigger Patterns | Backend Call | Example |
|--------|------------------|--------------|---------|
| `top_products` | "top product", "highest billing", "which product" | `query_service.top_products_by_billing_count()` | "Which products have the most billing docs?" |
| `broken_flows` | "broken flow", "delivered not billed", "incomplete" | `query_service.broken_flows()` | "Show me broken flows" |
| `trace_billing_flow` | "trace billing", "billing flow", + billing ID | `query_service.trace_billing_flow()` | "Trace billing document 90504248" |
| `graph_explore` | "explore", "show", "graph", "relationships" | Future feature | "Show connected documents" |
| `out_of_domain` | Weather, sports, news, etc. | None (guardrail) | "What's the weather?" |
| `unknown` | Vague or no match | Clarification | "Tell me something" |

## Guardrail Keywords

**In-Domain Keywords:**
- Products, materials, SKU, billing, sales order, delivery, invoice, payment, flow, trace, etc.

**Out-of-Domain Keywords:**
- Weather, temperature, sports, score, movie, music, news, joke, stock, crypto, etc.

## Response Format

All chat responses follow this structure:

```json
{
  "answer_text": "Natural language answer or clarification request",
  "intent": "top_products|broken_flows|trace_billing_flow|graph_explore|out_of_domain|unknown|error",
  "cited_data_summary": {
    "results": [...],
    "count": 10
  },
  "referenced_node_ids": ["product_123", "delivery_456"],
  "referenced_edge_ids": [],
  "requires_clarification": false
}
```

## No Breaking Changes

- All existing endpoints remain unchanged and functional
- Deterministic query backends are not modified
- Guardrails are keyword-based (no LLM calls required)
- LLM service is optional (graceful degradation if API key not set)

## Data Extraction from Prompts

The chat service automatically extracts structured data:
- **Billing Document ID**: Regex `\b(\d{8,})\b` (e.g., "90504248")
- **Limit**: Regex `(top|highest|first)\s+(\d+)` (e.g., "top 10 products")

## Fallback Behavior

1. **LLM Not Available**: Use pure deterministic routing (keyword patterns only)
2. **Query Returns Empty**: Synthesize appropriate "no results" message
3. **Prompt is Ambiguous**: Ask clarifying question with suggestions
4. **Billing Doc Not Found**: Return specific error message, ask for ID
5. **Out-of-Domain**: Guardrail rejection with system scope message

## Testing Checklist

### Sample Prompts to Test:

**In-Domain (Should work):**
```bash
# Top products
POST /api/chat
{"prompt": "Which products are associated with the highest number of billing documents?"}

# Top products with limit
POST /api/chat
{"prompt": "Show me the top 5 products by billing count"}

# Broken flows
POST /api/chat
{"prompt": "Show me all broken flows"}

# Trace billing
POST /api/chat
{"prompt": "Trace billing document 90504248"}

# Trace billing (missing ID - should clarify)
POST /api/chat
{"prompt": "Trace a billing document"}

# Graph exploration (future feature)
POST /api/chat
{"prompt": "Explore the graph"}
```

**Out-of-Domain (Should reject):**
```bash
POST /api/chat
{"prompt": "What's the weather today?"}

POST /api/chat
{"prompt": "Who won the Super Bowl?"}

POST /api/chat
{"prompt": "Tell me a joke"}
```

**Ambiguous (Should clarify):**
```bash
POST /api/chat
{"prompt": "hello"}

POST /api/chat
{"prompt": ""}
```

## Manual Commands to Run

1. **Verify files exist and have no syntax errors:**
   ```bash
   python -m py_compile backend/app/services/chat_service.py
   python -m py_compile backend/app/services/guardrail_service.py
   python -m py_compile backend/app/services/llm_service.py
   python -m py_compile backend/app/routers/chat.py
   ```

2. **Run backend server (if not running):**
   ```bash
   cd backend
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Test chat endpoint with curl:**
   ```bash
   curl -X POST http://127.0.0.1:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Which products have the most billing documents?"}'
   ```

## Production Considerations

- **Authentication**: Add if needed (currently open)
- **Rate Limiting**: Add if needed
- **Logging**: Currently uses print() for debug; upgrade to structured logging
- **LLM Integration**: Implement actual OpenAI/Anthropic calls in `llm_service.py`
- **Prompt History**: Add if multi-turn conversation needed
- **Analytics**: Track intent distribution for monitoring

## Code Quality

- ✅ No breaking changes to existing endpoints
- ✅ Deterministic routing prioritized over LLM
- ✅ All responses grounded in real backend data
- ✅ Guardrails work without LLM dependency
- ✅ Production-style error handling
- ✅ Type hints throughout
- ✅ Docstrings on all classes/methods
- ✅ No hallucinated answers
