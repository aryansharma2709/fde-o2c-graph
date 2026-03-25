# AI Coding Sessions Summary

This project was built using a combination of manual engineering work and AI-assisted iteration.

## Tools Used
- VS Code
- GitHub Copilot / agent-style coding assistance
- ChatGPT for architecture review, debugging support, and implementation refinement

## How AI Was Used
AI tools were used as a development accelerator, not as an unverified code generator. The workflow was:

1. Define the architecture and project phases
2. Scaffold implementation files and folder structure
3. Iterate on backend ingestion, graph projection, and API wiring
4. Debug schema mismatches, connection issues, and frontend/backend integration issues
5. Refine grounded chat behavior and UI interactions

## Key Workflows
### 1. Backend-first implementation
The project was built in layers:
- dataset ingestion into DuckDB
- graph projection (`graph_nodes`, `graph_edges`)
- deterministic query endpoints
- guarded chat routing layer
- frontend graph explorer + chat UI

### 2. Iterative debugging
AI assistance was especially helpful for:
- resolving DuckDB schema mismatches
- fixing database path inconsistencies
- aligning graph node/edge schemas with backend services
- fixing frontend request wiring and React Flow data mapping
- improving chat intent routing and grounded response formatting

### 3. Grounded-response strategy
The final system was intentionally designed so that:
- business answers come from deterministic backend queries
- chat responses are routed to supported query capabilities
- off-topic prompts are rejected
- no free-form LLM answer is returned without dataset-backed logic

## Representative Prompt / Debugging Patterns
Examples of the kinds of AI-assisted prompts/workflows used:
- scaffold backend structure for FastAPI + DuckDB
- fix ingestion path handling for partitioned JSONL collections
- align graph service schema with actual ingested DuckDB tables
- make `/api/ingest` idempotent
- route natural-language prompts to deterministic query functions
- fix frontend graph rendering and chat request wiring
- improve response formatting and graph-linked node highlighting

## Debugging Style
The implementation followed a tight loop:
- make one scoped change
- run locally
- inspect exact error
- patch only the failing layer
- re-test through Swagger and the UI

This reduced risk and helped keep the final app stable.

## Notes
- The final system emphasizes grounded engineering over unrestricted LLM generation.
- AI support was used heavily for speed and iteration, but all critical behavior was manually validated through local and deployed testing.
