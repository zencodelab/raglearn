"""
GovShield RAG API — FastAPI layer over the retrieval pipeline.

Exposes the RAG query engine (pgvector + RBAC + Ollama) as a REST API.
Run natively:  uvicorn api:app --reload --port 8000
Run via Docker: docker compose up govshield-api
"""

import logging
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from retrieval_app import get_query_engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GovShield RAG API",
    description=(
        "Secure offline RAG API with RBAC clearance pre-filtering. "
        "Queries are scoped to the caller's clearance level before vector retrieval."
    ),
    version="1.0.0",
)


# ── Request / Response models ─────────────────────────────────────────────────

class QueryRequest(BaseModel):
    text: str = Field(..., min_length=1, description="The question to ask")
    clearance: Literal["Public", "L1", "L2"] = Field(
        "L1",
        description="Caller's clearance level. Determines which document chunks are searchable.",
    )


class SourceChunk(BaseModel):
    file: str
    page: str | None = None
    score: float
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    clearance_used: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "GovShield RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "POST /query": "Submit a question with a clearance level",
            "GET /health": "Health check",
        },
    }


@app.get("/health", summary="Health check")
def health():
    """Returns 200 if the API is up. Does not verify DB or Ollama connectivity."""
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse, summary="Query the RAG pipeline")
def query(request: QueryRequest):
    """
    Submit a question to the RAG pipeline.

    - **text**: natural language question
    - **clearance**: `Public` | `L1` | `L2` — restricts which document chunks
      are eligible for retrieval (pre-filtered at the pgvector query level)

    Returns the synthesized answer and the top-K source chunks used.
    If no answer is found in the document corpus, the LLM returns:
    *"I cannot find the answer in the provided documents."*
    """
    try:
        engine = get_query_engine(user_clearance=request.clearance)
    except Exception as exc:
        logger.error("Failed to initialize query engine: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="RAG engine unavailable. Ensure Ollama is running and documents have been ingested.",
        )

    try:
        response = engine.query(request.text)
    except Exception as exc:
        logger.error("Query execution failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}")

    sources = [
        SourceChunk(
            file=node.node.metadata.get("file_name", "unknown"),
            page=node.node.metadata.get("page_label"),
            score=round(node.score, 4),
            snippet=node.node.get_content().strip().replace("\n", " ")[:200],
        )
        for node in response.source_nodes
    ]

    return QueryResponse(
        answer=response.response.strip(),
        sources=sources,
        clearance_used=request.clearance,
    )
