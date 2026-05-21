# 🛡️ GovShield: Secure Offline Local RAG Portal

An interactive, premium dark-themed, and **100% offline** Retrieval-Augmented Generation (RAG) system built to ensure complete data sovereignty and privacy. Designed for secure, air-gapped environments, GovShield processes and indexes documents entirely on your local machine, utilizing local embedding models and local LLMs via Ollama.

---

## 🎨 Key Features Implemented

*   **🔒 Complete Data Sovereignty**: Operates with absolute offline isolation. Zero API calls are made to third-party public clouds, preventing any external data leakage.
*   **⚡ Local GPU Acceleration**: Intelligently routes queries from inside Docker to your host Mac's native Ollama engine via `host.docker.internal`, preserving native Apple Silicon Metal GPU acceleration for fast inference times.
*   **📁 Persistent Storage Mounts**: Synchronizes your host's `./data` folder and persistent `./chroma_db` database inside the container in real time, keeping your indexes and documents accessible and editable.
*   **🧪 Multi-Model & Top-K Depth Flexibility**: Streamlit dashboard lets you seamlessly toggle retrieval depth (Top-K matching segments) and switch between lightweight models like `gemma3:4b` or `qwen2.5:7b` on the fly.
*   **🎛️ Cyber-Ops Security Dashboard**: Polished with a custom glassmorphic UI, Google Fonts (`Outfit` and `JetBrains Mono`), animated breathing status indicators, and hover-responsive source citation cards.
*   **🛡️ Secure Grounding Guardrails**: Prompt templates restrict the LLM to synthesized source context only. If the answer cannot be found in your local files, the system safe-guards against hallucinations by stating: *"I cannot find the answer in the provided documents."*

---

## 📂 Project Directory Structure

```text
raglearn/
├── data/                    # Secure local reference manuals
│   ├── it_support_faq.txt
│   ├── office_policies.txt
│   └── security_protocols.txt
├── chroma_db/               # Persistent Vector Database (created during ingestion)
├── ingestion.py             # Parses documents, splits into chunks, embeds, and saves to ChromaDB
├── retrieval_app.py         # Core vector retrieval engine & interactive terminal CLI
├── app.py                   # Premium Streamlit web application dashboard
├── requirements.txt         # Optimized, modular local LlamaIndex dependencies
├── Dockerfile               # Multi-layer Docker image construction
├── docker-compose.yml       # Host volume mounting & gateway connections
├── .dockerignore            # Build exclusion rules (ignores .venv and chroma_db context)
└── README.md                # This comprehensive user manual
```

---

## ⚙️ Setup Prerequisites

Ensure you have the following installed on your machine:
1.  **Python 3.9+**
2.  **Ollama** (Running natively on your macOS host)
3.  **Docker & Docker Compose** (Only required for running containerized)

### Local Ollama Models Cache
Ensure you have pulled the required models inside your Ollama environment:
```bash
# Pull local embedding model (384-dimensional)
ollama pull nomic-embed-text

# Pull the synthesis model
ollama pull gemma3:4b
```

---

## 🚀 How to Run Locally (Native Host)

Follow these terminal commands to run GovShield natively in your virtual environment:

### 1. Configure the Virtual Environment
```bash
# Initialize Python virtual environment
python3 -m venv .venv

# Activate the environment
source .venv/bin/activate

# Upgrade pip and install optimized requirements
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Ingest Reference Documents
Add text or PDF documents into the `./data/` folder, then run the ingestion pipeline to parse, chunk, embed, and store them in the Chroma vector database:
```bash
python ingestion.py
```

### 3. Run the Interactive CLI Query Tool
To query your documents directly inside your terminal, run the retrieval app:
```bash
# Run a single query
python retrieval_app.py "What is the network IP address for the floor printer?"

# Or enter interactive loop mode
python retrieval_app.py
```

### 4. Boot the Premium Streamlit Dashboard
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser to interact with the responsive dashboard.

---

## 🐳 How to Run with Docker (Recommended)

Running GovShield inside Docker isolates the web server while mapping database volumes and maintaining GPU speeds.

### 1. Build the Optimized Image
Thanks to `.dockerignore`, the context transfer is reduced to **`~150kB`** (excluding the massive `.venv` folder). The build process will execute in under 3 minutes:
```bash
docker compose build
```

### 2. Spin up the Container
Launch the container in detached background mode:
```bash
docker compose up -d
```
The Streamlit RAG portal will boot and be served live at **`http://localhost:8501`**.

### 3. Run Ingestion Inside the Container
If you drop new files into your host `./data/` folder, you can run the ingestion pipeline directly inside the active container to refresh the database:
```bash
docker compose exec govshield python ingestion.py
```

### 4. Useful Management Commands
```bash
# Stream live application container logs
docker compose logs -f

# Shut down and stop the container
docker compose down

# Re-build and restart after changing configuration code
docker compose up -d --build
```

---

## 🛡️ RAG Security Grounding Proof

To ensure the security framework is operating as designed, GovShield has been tested with in-domain and out-of-domain queries:

1.  **In-Domain Question:** *"What is the required temperature for the server room?"*
    *   *Result:* Synthesizes and matches context inside `security_protocols.txt` returning: *"strictly between 68 and 72 degrees Fahrenheit"*.
2.  **Out-of-Domain Question:** *"Who won the FIFA World Cup in 2022?"*
    *   *Result:* The secure prompt template blocks the query, preventing cloud hallucinations, and returns: *"I cannot find the answer in the provided documents."*
