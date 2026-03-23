# Deployment

## Overview

- **Frontend**: React + Vite deployed to Vercel (CDN-distributed)
- **Backend**: FastAPI deployed to Render (containerized)
- **Data**: DuckDB file co-located with backend
- **CI/CD**: GitHub Actions for automated deploy-on-push

---

## Frontend Deployment (Vercel)

### Prerequisites

- GitHub repository connected to Vercel account
- Node.js 18+ installed locally
- `vercel` CLI: `npm install -g vercel`

### Environment Variables

Create `.env.production` in frontend root:

```env
VITE_API_URL=https://fde-o2c-graph-backend.render.com
VITE_APP_NAME=O2C Explorer
```

Vercel dashboard settings:
```
Project: fde-o2c-graph-frontend
Framework: Vite
Root directory: ./frontend
Build command: npm run build
Output directory: dist
Environment variables:
  VITE_API_URL = https://fde-o2c-graph-backend.render.com
```

### Build & Deploy

```bash
cd frontend
npm install
npm run build
vercel deploy --prod
```

Or push to `main` branch for automatic Vercel deployment:
```bash
git push origin main
```

**Verification**
- Wait ~2 min for build
- Check Vercel dashboard for deployment status
- Visit https://fde-o2c-graph.vercel.app
- Open DevTools console to verify API_URL is set

### CORS Configuration

Vercel domain is auto-whitelisted in backend CORS settings:
```python
# backend/app/main.py
origins = [
    "https://fde-o2c-graph.vercel.app",
    "http://localhost:3000",  # dev
]
```

---

## Backend Deployment (Render)

### Prerequisites

- Render.com account (free tier OK for assignment)
- GitHub repository with backend code
- DuckDB file in `data/sap-orders.duckdb` (or fetch script)

### Environment Setup

Create `.env.production` file (not committed):

```env
DATABASE_PATH=data/sap-orders.duckdb
OPENAI_API_KEY=sk-...
ENVIRONMENT=production
LOG_LEVEL=info
CORS_ORIGINS=https://fde-o2c-graph.vercel.app,http://localhost:3000
```

**On Render Dashboard**:
```
Service: fde-o2c-graph-backend
Environment: Python 3.11
Build command: pip install -r requirements.txt
Start command: gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
Environment variables:
  DATABASE_PATH = data/sap-orders.duckdb
  OPENAI_API_KEY = sk-...
  ENVIRONMENT = production
```

### Dockerfile (Optional, but recommended)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

ENV DATABASE_PATH=data/sap-orders.duckdb
ENV ENVIRONMENT=production

CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
```

Build & push:
```bash
docker build -t fde-o2c-graph-backend:latest .
docker tag fde-o2c-graph-backend:latest <registry>/fde-o2c-graph-backend:latest
docker push <registry>/fde-o2c-graph-backend:latest
```

### Deploy via Render

**Option 1: Direct Push (no Docker)**

1. Create new Web Service on Render
2. Connect GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000`
5. Add environment variables (see above)
6. Deploy!

**Option 2: Docker**

1. Create new Web Service on Render
2. Point to Docker image registry (Docker Hub / private)
3. Deploy

### Database File Management

**Option A: Commit to Git**
- Check in `data/sap-orders.duckdb` to repo (if < 100MB)
- Render auto-includes in deployment

**Option B: Download at Runtime**
- Store DuckDB file in Render Disk or S3
- Add startup script:
  ```python
  # backend/app/startup.py
  if not os.path.exists('data/sap-orders.duckdb'):
      download_from_s3('s3://bucket/sap-orders.duckdb', 'data/sap-orders.duckdb')
  ```

**Option C: Embedded in Image**
- Build Docker image with DuckDB file
- COPY into Dockerfile

### Health Check

Render probes: `GET /api/health` every 10 seconds

Response must be 200 OK:
```json
{"status": "healthy", "timestamp": "...", "version": "0.1.0"}
```

### Logs & Monitoring

View Render logs:
```bash
# Via Render dashboard → Services → Logs
# Or via Render CLI
render logs --service fde-o2c-graph-backend --follow
```

Key metrics to monitor:
- Request latency (should be < 500ms for graph queries)
- Error rate (< 1% for valid queries)
- DuckDB query execution time (< 5s max)
- LLM API latency (varies, timeout at 30s)

---

## Data Migration & Seeding

### Initial Data Load

```bash
# 1. Unzip dataset
unzip data/raw/sap-order-to-cash-dataset.zip -d data/raw/

# 2. Transform into DuckDB (Python script)
python scripts/load_dataset.py

# 3. Verify schema
python -c "import duckdb; conn = duckdb.connect('data/sap-orders.duckdb'); print(conn.execute('SHOW TABLES').fetchall())"

# 4. Create indices
python scripts/create_indices.py

# 5. Commit to repo or upload to S3
git add data/sap-orders.duckdb
git commit -m "Add DuckDB with O2C data"
```

### Schema Version Control

Store DDL in `backend/data/schema.sql`:

```sql
-- Version 1: Initial schema
-- Created: 2026-03-24

CREATE TABLE IF NOT EXISTS orders (...);
CREATE TABLE IF NOT EXISTS order_items (...);
-- ... etc

CREATE INDEX IF NOT EXISTS idx_order_supplier ON orders(supplier_id);
```

Track migrations:
```
backend/data/
├── schema.sql           # Current schema
├── migrations/
│   ├── 001_initial_schema.sql
│   └── 002_add_payment_method_idx.sql
```

---

## Local Development Setup

### Backend (FastAPI)

```bash
# 1. Clone repo
git clone https://github.com/your-org/fde-o2c-graph.git
cd fde-o2c-graph

# 2. Create venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Load data (if not already present)
unzip data/raw/sap-order-to-cash-dataset.zip -d data/raw/
python scripts/load_dataset.py

# 5. Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Visit http://localhost:8000/docs for API docs
```

### Frontend (React + Vite)

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Create .env for dev
echo "VITE_API_URL=http://localhost:8000" > .env.development.local

# 4. Run dev server
npm run dev

# 5. Visit http://localhost:5173
```

### Docker Compose (Full Stack)

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_PATH: data/sap-orders.duckdb
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://backend:8000
    depends_on:
      - backend
```

Run:
```bash
docker-compose up
# Visit http://localhost:5173
```

---

## CI/CD Pipeline (GitHub Actions)

### Workflow: Deploy on Push to Main

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Vercel & Render

on:
  push:
    branches:
      - main

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Render
        uses: actions/github-script@v6
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            // Trigger Render webhook
            await fetch('https://api.render.com/deploy/...',
              { method: 'POST' }
            )

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Vercel
        run: |
          npm install -g vercel
          vercel deploy --prod --token ${{ secrets.VERCEL_TOKEN }} ./frontend
```

### Test Before Deploy

```yaml
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - run: |
          pip install -r requirements.txt
          pytest tests/ -v
```

---

## Monitoring & Alerting

### Render Monitoring

- CPU usage > 80%
- Memory usage > 90%
- Response time > 2s (p95)
- Error rate > 5%

### Vercel Monitoring

- Build failures
- Deploy errors
- Function execution timeouts

### Custom Metrics

Add to backend:

```python
from prometheus_client import Counter, Histogram

query_counter = Counter('queries_total', 'Total queries', ['status'])
query_latency = Histogram('query_latency_seconds', 'Query latency')

@app.get('/api/chat')
async def chat(req: ChatRequest):
    with query_latency.time():
        try:
            result = execute_query(req.message)
            query_counter.labels(status='success').inc()
            return result
        except Exception as e:
            query_counter.labels(status='error').inc()
            raise
```

Expose metrics at `/metrics` for Prometheus scraping.

---

## Rollback Procedure

### Frontend (Vercel)

```bash
# View deployments
vercel ls

# Rollback to previous
vercel rollback prod-xyz123
```

Or revert Git commit and push to main:
```bash
git revert HEAD
git push origin main
```

### Backend (Render)

```bash
# Via Render dashboard:
# Services → fde-o2c-graph-backend → Activity → Previous Deployments → Rollback
```

Or redeploy specific commit:
```bash
git push origin commit-hash:main
```

---

## Production Checklist

- [ ] Environment variables set securely (not in git)
- [ ] CORS origins restricted (Vercel domain only)
- [ ] Database file has < 100MB footprint (within limits)
- [ ] LLM API key rotated (if shared)
- [ ] Rate limiting enabled (20 req/min for /api/chat)
- [ ] Health checks passing
- [ ] Error handling tested (timeouts, OOM)
- [ ] Logs retention configured
- [ ] HTTPS enforced (automatic on Vercel/Render)
- [ ] Database backups scheduled (if not ephemeral)

---

## Scaling Considerations (Future)

- **DuckDB**: Single-process, but suitable for < 1GB data
- **FastAPI**: Easily horizontal scalable behind load balancer
- **Frontend**: Already CDN-distributed by Vercel
- **Database Replication**: Copy DuckDB file to multiple backends
- **Caching**: Add Redis for repeated queries
- **Async Tasks**: Offload LLM calls to background queue

---

## Troubleshooting

**Backend won't start**
```bash
# Check logs
render logs --service fde-o2c-graph-backend --tail 50

# Verify database file exists
ls -la data/sap-orders.duckdb
```

**CORS errors in browser**
```
# Verify backend CORS config includes frontend URL
curl -H "Origin: https://fde-o2c-graph.vercel.app" http://localhost:8000/api/health -v
```

**Out of memory on Render**
```
# Check data size
du -h data/sap-orders.duckdb

# Reduce workers
gunicorn -w 2 ...  # instead of 4
```

**Chat queries timing out**
```
# Add timeout to LLM service
llm_response = call_llm(query, timeout=10)  # 10s max
```
