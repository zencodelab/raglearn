import os
import sys
import logging
import pypdf
from pathlib import Path
import psycopg2
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    Settings,
    Document,
)
from llama_index.core.readers.base import BaseReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.postgres import PGVectorStore

class PyPDFLocalReader(BaseReader):
    """Secure, local, 100% offline multi-page PDF reader."""
    def load_data(self, file: Path, extra_info: dict = None) -> list:
        docs = []
        with open(file, "rb") as f:
            pdf = pypdf.PdfReader(f)
            num_pages = len(pdf.pages)
            for page_idx in range(num_pages):
                page = pdf.pages[page_idx]
                text = page.extract_text() or ""
                metadata = {
                    "file_name": file.name,
                    "page_label": str(page_idx + 1),
                }
                if extra_info:
                    metadata.update(extra_info)
                docs.append(Document(text=text, metadata=metadata))
        return docs

# Configure logging to console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting local RAG ingestion pipeline...")
    
    # 1. Initialize local Ollama Embedding Model
    logger.info("Initializing local embedding model (nomic-embed-text)...")
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    logger.info(f"Using Ollama base URL: {ollama_base_url}")
    try:
        embed_model = OllamaEmbedding(
            model_name="nomic-embed-text",
            base_url=ollama_base_url,
            request_timeout=60.0
        )
        # Configure LlamaIndex to use this embedding model globally
        Settings.embed_model = embed_model
    except Exception as e:
        logger.error(f"Failed to initialize Ollama embedding model. Is Ollama running? Error: {e}")
        sys.exit(1)

    # 2. Configure Chunking & Node Parsing
    logger.info("Configuring document chunker (Size: 500 chars, Overlap: 50 chars)...")
    chunk_size = 500
    chunk_overlap = 50
    node_parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    # 3. Read documents from the data/ directory
    data_dir = "./data"
    if not os.path.exists(data_dir) or not os.listdir(data_dir):
        logger.error(f"Data directory '{data_dir}' is empty or does not exist. Please place documents there first.")
        sys.exit(1)
        
    try:
        reader = SimpleDirectoryReader(
            input_dir=data_dir,
            file_extractor={".pdf": PyPDFLocalReader()}
        )
        documents = reader.load_data()
        logger.info(f"Successfully loaded {len(documents)} document pages/segments.")
        
        # Helper to assign clearance levels based on file name
        def get_clearance_level(file_name):
            file_name_lower = file_name.lower()
            if "security_protocols" in file_name_lower or "internal_procedures" in file_name_lower:
                return "L2"
            elif "it_support_faq" in file_name_lower or "office_policies" in file_name_lower:
                return "L1"
            else:
                return "Public"

        # Inject clearance levels into document metadata for RBAC pre-filtering
        logger.info("Injecting Role-Based Access Control (RBAC) clearance levels...")
        for doc in documents:
            file_name = doc.metadata.get("file_name", "")
            clearance = get_clearance_level(file_name)
            doc.metadata["clearance_level"] = clearance
            page_info = f" (Page {doc.metadata['page_label']})" if "page_label" in doc.metadata else ""
            logger.info(f" -> Tagged document '{file_name}'{page_info} with clearance level: {clearance}")
    except Exception as e:
        logger.error(f"Error loading documents: {e}")
        sys.exit(1)

    # 4. Set up local PostgreSQL pgvector Store
    logger.info("Setting up local PostgreSQL pgvector vector database...")
    postgres_host = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port = int(os.environ.get("POSTGRES_PORT", "5432"))
    postgres_db = os.environ.get("POSTGRES_DB", "govshield_db")
    postgres_user = os.environ.get("POSTGRES_USER", "govshield_user")
    postgres_password = os.environ.get("POSTGRES_PASSWORD", "govshield_secure_pwd")
    table_name = "local_rag_collection"
    
    # Establish a connection using psycopg2 to drop the existing table for a clean re-ingestion
    try:
        logger.info(f"Connecting to database to perform clean re-indexing drop of table 'data_{table_name}'...")
        conn = psycopg2.connect(
            host=postgres_host,
            port=postgres_port,
            dbname=postgres_db,
            user=postgres_user,
            password=postgres_password
        )
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute(f"DROP TABLE IF EXISTS data_{table_name} CASCADE;")
            logger.info(f"Successfully dropped table 'data_{table_name}' for clean re-run.")
        conn.close()
    except Exception as e:
        logger.warning(f"Could not drop table data_{table_name} (it might not exist yet): {e}")

    try:
        # Initialize PGVectorStore
        vector_store = PGVectorStore.from_params(
            host=postgres_host,
            port=postgres_port,
            database=postgres_db,
            user=postgres_user,
            password=postgres_password,
            table_name=table_name,
            embed_dim=768,  # nomic-embed-text embedding dimension
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
    except Exception as e:
        logger.error(f"Error setting up PGVectorStore: {e}")
        sys.exit(1)

    # 5. Build the Vector Store Index (Embed & Store)
    logger.info("Splitting documents, generating embeddings via Ollama, and saving to PostgreSQL...")
    try:
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=[node_parser],
            show_progress=True
        )
        logger.info("Ingestion pipeline completed successfully!")
        logger.info(f"Vector Database saved in PostgreSQL table 'data_{table_name}' inside DB '{postgres_db}'.")
    except Exception as e:
        logger.error(f"Failed to generate embeddings and index documents: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
