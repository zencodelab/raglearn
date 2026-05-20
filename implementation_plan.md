# Implementation Plan: Local Government RAG Proof-of-Concept

The goal of this implementation plan is to scaffold a local Proof-of-Concept (PoC) for the Air-Gapped/Government RAG architecture we just designed. This PoC will run entirely locally on your machine without using any external APIs, mimicking a highly secure, private environment.

## User Review Required

> [!IMPORTANT]
> The full production architecture requires large GPU resources (like A100s). For this PoC, we will target open-source dependencies and models that can run locally on your Mac (e.g., using Ollama for LLMs and `pgvector` or `Chroma` for the vector database).
> Please confirm if you are okay with spinning up this local PoC, and if you already have Ollama or Docker installed.

## Proposed Changes

We will create a Python-based backend in your `raglearn` workspace.

---

### Infrastructure Setup

We will set up the local components necessary for the RAG pipeline.
*   **LLM Engine**: We will pull a lightweight instructional model using Ollama (e.g., `llama3:8b` or `mistral`).
*   **Vector Database**: We will use an embedded local Vector DB (`ChromaDB`) to avoid the complexity of a dockerized `pgvector` for the PoC, or we can use `pgvector` if you prefer a closer-to-production setup. 

---

### Python Application Structure

We will create a foundational LlamaIndex or LangChain RAG pipeline.

#### [NEW] [requirements.txt](file:///Users/afsalaazeez/Workspace/github/zencodelab/raglearn/requirements.txt)
Define local-only dependencies: `llama-index`, `llama-index-llms-ollama`, `llama-index-embeddings-huggingface`, `chromadb`, and `gradio` or `streamlit` for the UI.

#### [NEW] [ingestion.py](file:///Users/afsalaazeez/Workspace/github/zencodelab/raglearn/ingestion.py)
Script to parse local documents (e.g., PDFs), chunk them, and embed them using a local Hugging Face embedding model (like `BAAI/bge-small-en-v1.5`), then store them in the local vector DB.

#### [NEW] [retrieval_app.py](file:///Users/afsalaazeez/Workspace/github/zencodelab/raglearn/retrieval_app.py)
The main query engine. It will take a user query, embed it, search the vector database, and route the context and query to the local Ollama LLM to generate the final response.

## Open Questions

> [!WARNING]
> 1. Do you have **Ollama** installed on your Mac? If not, we will need to install it first to serve local models.
> 2. For the Vector DB, is a fast embedded database like **ChromaDB** acceptable for the PoC, or do you want a heavier Dockerized **pgvector** setup?
> 3. Do you have a specific test dataset (PDFs/docs) you want to use?

## Verification Plan

### Automated Tests
*   Run the ingest script against a sample `data/` folder and verify vector creation.

### Manual Verification
*   Start the `retrieval_app.py` UI.
*   Ask a question related to the sample documents.
*   Verify in the console logs that **no external HTTP requests** are made during the retrieval or generation phases, ensuring completely offline operation.
