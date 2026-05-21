Ran command: `git rm -r --cached chroma_db`
Viewed .gitignore:1-38
Ran command: `git commit -m "dockerise"`

Now that the baseline RAG core is fully operational, style-optimized, and containerized, the project is in a perfect state to be upgraded from a Proof-of-Concept to an **enterprise-grade secure RAG system**. 

Here are the four most valuable advanced features we can implement next. 

---

### Option 1: 🔐 Role-Based Access Control (RBAC) / Clearance Filtering
In secure government or corporate networks, access control is paramount. We can implement metadata clearance tags to restrict which documents a user can search.
*   **What we will do:**
    1.  Update the ingestion script ([ingestion.py](file:///Users/afsalaazeez/Workspace/github/zencodelab/raglearn/ingestion.py)) to tag nodes with clearance metadata (`clearance: "L2"`, `"L1"`, or `"Public"`) based on their document type.
    2.  Add a dropdown in the Streamlit sidebar to select the "Active User Clearance Level".
    3.  Configure LlamaIndex's `MetadataFilters` in [app.py](file:///Users/afsalaazeez/Workspace/github/zencodelab/raglearn/app.py) so the vector store query **automatically pre-filters** chunks *before* retrieving them. A user with "Public" clearance will never be able to retrieve or see snippets from "L2" files.

---

### Option 2: 📄 Multi-Page PDF Ingestion & OCR Parsing
Currently, we ingest flat text files. In a production environment, you will have structured manuals, scanned documents, and PDFs.
*   **What we will do:**
    1.  Add multi-page PDF reference manuals containing tables and formatted layouts to your `data/` directory.
    2.  Upgrade the ingestion script with LlamaIndex's `PyMuPDFReader` or `pypdf` parsers.
    3.  Implement advanced layout-aware chunking strategies (e.g., splitting by sections or pages rather than naive character counts) to maintain layout hierarchy.

---

### Option 3: 🐘 Vector Database Scale-up (PostgreSQL + `pgvector`)
ChromaDB is a fantastic embedded store, but for production scale, database isolation and standard query integrations are required.
*   **What we will do:**
    1.  Add a containerized **PostgreSQL** service featuring the `pgvector` extension directly inside your [`docker-compose.yml`](file:///Users/afsalaazeez/Workspace/github/zencodelab/raglearn/docker-compose.yml).
    2.  Refactor LlamaIndex to use the `PGVectorStore` connector instead of `ChromaVectorStore`.
    3.  This establishes a multi-container network inside Docker where your app and database run as isolated, secure services.

---

### Option 4: 📊 Local Offline Quality Evaluation (RAG Triad)
How do we know if our chunk size (`500` chars), retrieval depth (`Top-K: 3`), and local model (`gemma3`) are performing accurately?
*   **What we will do:**
    1.  Build an offline evaluation script that runs test queries against the database.
    2.  Utilize a local evaluation harness (scoring faithfulness, answer relevance, and context recall) entirely offline using your local LLM.
    3.  Output a mathematical score sheet showing your RAG pipeline's overall retrieval accuracy.

---

### 💬 Which step would you like to take next? 
*(I highly recommend **Option 1 (RBAC)** as it aligns perfectly with the secure, sovereign, and private positioning of **GovShield**, showing how security is maintained at the metadata chunk layer!)*