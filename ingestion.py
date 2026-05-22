import os
import sys
import logging
import pypdf
from pathlib import Path
import chromadb
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
from llama_index.vector_stores.chroma import ChromaVectorStore

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

    # 4. Set up local ChromaDB Vector Store
    logger.info("Setting up local ChromaDB persistent vector database...")
    db_path = "./chroma_db"
    collection_name = "local_rag_collection"
    
    try:
        # Initialize the Chroma DB client on disk
        chroma_client = chromadb.PersistentClient(path=db_path)
        
        # If the collection already exists, we will delete it to prevent duplicate index entries on successive runs
        existing_collections = [c.name for c in chroma_client.list_collections()]
        if collection_name in existing_collections:
            logger.info(f"Collection '{collection_name}' already exists. Recreating it to refresh the index.")
            chroma_client.delete_collection(name=collection_name)
            
        # Create a fresh collection
        chroma_collection = chroma_client.create_collection(name=collection_name)
        
        # Connect Chroma DB to LlamaIndex vector store
        vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
    except Exception as e:
        logger.error(f"Error setting up ChromaDB: {e}")
        sys.exit(1)

    # 5. Build the Vector Store Index (Embed & Store)
    logger.info("Splitting documents, generating embeddings via Ollama, and saving to ChromaDB...")
    try:
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            transformations=[node_parser],
            show_progress=True
        )
        logger.info("Ingestion pipeline completed successfully!")
        logger.info(f"Vector Database saved locally at '{db_path}' in collection '{collection_name}'.")
    except Exception as e:
        logger.error(f"Failed to generate embeddings and index documents: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
