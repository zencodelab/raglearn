# 🛡️ GovShield: Secure Offline RAG Portal

A **100% offline** Retrieval-Augmented Generation (RAG) system with role-based access control, built for complete data sovereignty. Documents are ingested, chunked, embedded, and queried entirely on-device — zero API calls to third-party clouds.

**Stack:** LlamaIndex · PostgreSQL pgvector · Ollama · FastAPI · Streamlit · Docker

---

## Architecture

```
Documents (PDF/TXT)
        │
        ▼
  [ingestion.py]
  ┌─────────────────────────────────────────┐
  │ 1. Parse (pypdf for multi-page PDFs)    │
  │ 2. Chunk (SentenceSplitter 500/50)      │
  │ 3. Tag clearance level (L1/L2/Public)   │  ← RBAC metadata
  │ 4. Embed (Ollama nomic-embed-text 768d) │
  │ 5. Store → PostgreSQL pgvector          │
  └─────────────────────────────────────────┘
        │
        ▼
  [retrieval_app.py / app.py / api.py]
  ┌─────────────────────────────────────────┐
  │ 1. Pre-filter by user clearance level   │  ← RBAC enforcement
  │ 2. Vector similarity search (Top-K)     │
  │ 3. Synthesize via Ollama LLM            │
  │ 4. Refuse if answer not in documents    │  ← grounding guardrail
  └─────────────────────────────────────────┘
        │
        ├── Streamlit UI  (port 8501)
        ├── Interactive CLI  (retrieval_app.py)
        └── FastAPI REST API  (port 8000)  ← api.py
```

---

## Key Features

- **Role-Based Access Control (RBAC):** Documents are tagged `L1`, `L2`, or `Public` during ingestion. Queries are pre-filtered at the vector store level before retrieval — a user with `L1` clearance cannot retrieve `L2` chunks even if their query is semantically similar.
- **Multi-page PDF ingestion:** Custom `PyPDFLocalReader` extracts text per page with page-level metadata, enabling source citation down to the exact page.
- **PostgreSQL pgvector backend:** Production-grade vector storage in a containerized PostgreSQL instance with the `pgvector` extension (768-dimensional embeddings from `nomic-embed-text`).
- **Grounding guardrail:** Prompt template restricts the LLM to retrieved context only. Returns *"I cannot find the answer in the provided documents."* for out-of-scope queries.
- **REST API:** FastAPI server (`api.py`) exposes `POST /query` for programmatic access — same RBAC pre-filtering, Pydantic-validated request/response, auto-generated `/docs` (Swagger UI).
- **Dual interface:** Streamlit web dashboard + interactive CLI (`retrieval_app.py`) for terminal use.
- **Apple Silicon optimised:** Docker routes LLM/embedding requests to the host Ollama engine via `host.docker.internal`, preserving Metal GPU acceleration.

---

## Project Structure

```
raglearn/
├── data/                    # Place your documents here (PDF, TXT)
│   ├── it_support_faq.txt
│   ├── office_policies.txt
│   ├── security_protocols.txt
│   └── L1_office_policies.pdf
├── ingestion.py             # Ingest pipeline: parse → chunk → RBAC tag → embed → pgvector
├── retrieval_app.py         # CLI query engine with RBAC pre-filtering
├── app.py                   # Streamlit dashboard (model switcher, Top-K control, source cards)
├── api.py                   # FastAPI REST server (POST /query, GET /health)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml       # Three services: pgvector DB + Streamlit app + FastAPI
└── .dockerignore
```

---

## Prerequisites

- **Python 3.9+**
- **Ollama** running natively on the host (not inside Docker)
- **Docker & Docker Compose** (recommended path; also works natively with a local PostgreSQL)

Pull the required Ollama models:
```bash
ollama pull nomic-embed-text   # embedding model (768-dimensional)
ollama pull gemma3:4b          # synthesis LLM (or qwen2.5:7b)
```

---

## Running with Docker (Recommended)

The `docker-compose.yml` defines three services:
- **`db`** — `pgvector/pgvector:pg16` PostgreSQL instance, port 5432, named volume `pgdata`
- **`govshield`** — Streamlit dashboard on port 8501, connects to `db`
- **`govshield-api`** — FastAPI server on port 8000 (same image, command override to `uvicorn api:app`)

### 1. Start both services
```bash
docker compose up -d
```

### 2. Ingest your documents
Add files to `./data/`, then run ingestion inside the running container:
```bash
docker compose exec govshield python ingestion.py
```

### 3. Open the dashboard
Navigate to **`http://localhost:8501`**

### Useful commands
```bash
docker compose logs -f          # stream live logs
docker compose down             # stop both services
docker compose up -d --build    # rebuild after code changes
```

---

## Running Natively (Local PostgreSQL)

### 1. Set up Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Start PostgreSQL with pgvector
```bash
docker run -d \
  --name govshield-pgvector \
  -e POSTGRES_DB=govshield_db \
  -e POSTGRES_USER=govshield_user \
  -e POSTGRES_PASSWORD=govshield_secure_pwd \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 3. Ingest documents
```bash
python ingestion.py
```

### 4. Query via CLI
```bash
# Single query
python retrieval_app.py "What is the VPN policy for remote access?"

# Interactive loop
python retrieval_app.py
```

### 5. Launch Streamlit dashboard
```bash
streamlit run app.py
```

---

## REST API

The FastAPI server exposes `POST /query` with RBAC pre-filtering. Auto-generated Swagger UI at `/docs`.

### Start the API server

**Docker:**
```bash
docker compose up -d govshield-api
```

**Natively (after activating venv):**
```bash
uvicorn api:app --reload --port 8000
```

### Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/query` | Submit a question with clearance level |
| `GET` | `/health` | Liveness check |
| `GET` | `/docs` | Swagger UI |

### Example requests

```bash
# Public-clearance query (returns only Public-tagged chunks)
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"text": "What are the office hours?", "clearance": "Public"}'

# L2 clearance — full document corpus available
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"text": "What are the server room temperature requirements?", "clearance": "L2"}'
```

### Example response

```json
{
  "answer": "The server room must maintain a temperature between 18°C and 24°C...",
  "sources": [
    {
      "file": "security_protocols.txt",
      "page": null,
      "score": 0.8742,
      "snippet": "Server room temperature must be maintained between 18°C and 24°C at all times..."
    }
  ],
  "clearance_used": "L2"
}
```

---

## RBAC Clearance Levels

Clearance is assigned during ingestion based on filename:

| Filename pattern | Clearance |
|---|---|
| `security_protocols*`, `*internal_procedures*` | `L2` |
| `it_support_faq*`, `office_policies*` | `L1` |
| Everything else | `Public` |

Query engine respects clearance hierarchy:
- `Public` → can only retrieve `Public` chunks
- `L1` → retrieves `Public` + `L1`
- `L2` → retrieves all

Change the active clearance in `retrieval_app.py`:
```python
query_rag("your question", user_clearance="L1")
```

---

## Grounding Verification

| Query | Expected result |
|---|---|
| *"What temperature must the server room maintain?"* | Retrieves from `security_protocols.txt` — answers correctly |
| *"Who won the FIFA World Cup in 2022?"* | Returns: *"I cannot find the answer in the provided documents."* |
