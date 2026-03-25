# Deployment Guide

This project is deployed using Render for both backend and frontend.

## Deployment Overview

### Backend
- Platform: Render Web Service
- Framework: FastAPI
- Start command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`

### Frontend
- Platform: Render Static Site
- Framework: React + Vite
- Build output: `frontend/dist`

---

## Backend Deployment (Render Web Service)

### Service Type
Create a **Web Service** in Render.

### Repository
Connect the public GitHub repository.

### Build / Start Settings

If deploying from repo root:

**Build Command**
```bash
pip install -r requirements.txt
```

## Start Command
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

## Python Version

Pin Python to 3.11.11 using one or both of:
.python-version

Create a repo-root file:
```bash
3.11.11
```
Environment Variable
In Render backend service settings:
```bash
PYTHON_VERSION=3.11.11
```
Environment Variables
Only add variables your backend actually needs.
If no external LLM provider is enabled, no additional environment variables are required beyond deployment configuration.
Backend Verification
After deployment, verify:

```bash
/docs loads
POST /api/ingest succeeds
/api/query/top-products works
/api/chat works
```

## Frontend Deployment (Render Static Site)
Service Type

Create a Static Site in Render.

Repository

Use the same GitHub repository.

## Root Directory
```bash
frontend
```
## Build Settings

Build Command
```bash
npm install && npm run build
```
Publish Directory
```bash
dist
```
Frontend Environment Variable

In Render Static Site environment settings, add:
```bash
VITE_API_BASE_URL=https://YOUR-BACKEND-RENDER-URL.onrender.com
```

Replace with the real backend Render URL.

Frontend Verification

After deployment, verify:

the app loads
graph loads
Ingest Data button works
chat can call backend
trace / broken flows / top products prompts work
off-topic prompt is rejected



## Common Deployment Issues
1. Python version mismatch

If backend build fails on Render with Pydantic / Rust / pydantic-core issues, ensure Render is using:

3.11.11

not Python 3.14.

2. Frontend cannot call backend

Usually caused by:

wrong VITE_API_BASE_URL
backend sleeping / cold start
backend CORS restrictions
3. TypeScript frontend build fails

Fix local build first:

cd frontend
npm run build

Only redeploy after local build succeeds.

4. Missing dataset / empty graph

The graph is built after running:

POST /api/ingest

This step must succeed on the deployed backend before graph/query/chat endpoints have usable data.


## Recommended Smoke Test After Deployment
## Backend
open /docs
run POST /api/ingest
run GET /api/query/top-products?limit=10
run GET /api/query/broken-flows
run GET /api/query/trace/billing/90504248
run POST /api/chat

## Frontend
open live app
click Ingest Data
ask:
Which products are associated with the highest number of billing documents?
Trace billing document 90504248
Show broken flows
What is the weather today?

## Final Deployment Notes

This project uses a grounded architecture:

relational tables are the source of truth
graph nodes/edges are derived projections
deterministic query endpoints power business logic
chat is a routing/formatting layer over dataset-backed answers

This makes deployment simpler and reduces the risk of non-deterministic behavior in the live demo.
