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

## 2. Backend setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
 ```
3. Frontend setup
```bash
cd frontend
npm install
npm run dev
```
5. Frontend environment

Create:

frontend/.env

with:

VITE_API_BASE_URL=http://127.0.0.1:8000
Deployment

This project is deployed using Render:

backend: Render Web Service
frontend: Render Static Site

See docs/deployment.md for the full deployment steps.

Suggested Demo Flow

A short demo can show:

ingest the dataset
inspect the graph overview
ask for top products by billing documents
trace a billing document
show broken flows
ask an unrelated prompt and show guardrail rejection

See docs/demo-script.md for a presentation flow.

Repository Structure
backend/         FastAPI backend
frontend/        React + TypeScript frontend
docs/            architecture, deployment, demo notes
scripts/         helper scripts
sessions/        AI workflow summary / transcripts
data/            raw dataset (local development)
AI-Assisted Development Note

AI tools were actively used during implementation for:

scaffolding
debugging
architecture iteration
frontend/backend integration
error isolation
refinement of guarded chat behavior

However, final business answers are intentionally grounded in deterministic backend logic, not unconstrained AI generation.

See:

sessions/README.md
Limitations
the initial graph view is sample-based until chat or node exploration expands local context
natural-language support is bounded to supported O2C intents
no authentication layer is included
no unrestricted NL-to-SQL generation is used
graph exploration is optimized for demo clarity rather than large-scale graph analytics
Submission Contents

This submission includes:

a public GitHub repository
a working live demo
architecture and deployment documentation
AI coding session summary / logs
Final Note

This project emphasizes grounded engineering over speculative intelligence:

relational data remains the source of truth
graph structures are derived for exploration
required business questions are answered deterministically
the chat layer improves usability without sacrificing grounding

After pasting that into `README.md`, do this:

```bash
git add README.md
git commit -m "Update README for final submission"
git push origin main
```
---
<img width="1887" height="867" alt="image" src="https://github.com/user-attachments/assets/bc602f17-f2eb-43ae-acf2-5d08931cdbfa" />
<img width="695" height="636" alt="image" src="https://github.com/user-attachments/assets/8baf4853-f0d2-4d1a-bb86-7c30cce0ae65" />
<img width="1890" height="847" alt="image" src="https://github.com/user-attachments/assets/8f7249a2-8b20-4995-9bcb-131d0bb6e359" />
<img width="649" height="385" alt="image" src="https://github.com/user-attachments/assets/cff2e32e-ea51-4d80-8a29-965ba2bb6247" />
<img width="1229" height="848" alt="image" src="https://github.com/user-attachments/assets/267808d8-6f6a-4113-9096-563c7be5de7d" />
<img width="662" height="869" alt="image" src="https://github.com/user-attachments/assets/891bc490-e50f-42c9-af1d-49813b964513" />







## Notes
- The final system emphasizes grounded engineering over unrestricted LLM generation.
- AI support was used heavily for speed and iteration, but all critical behavior was manually validated through local and deployed testing.
