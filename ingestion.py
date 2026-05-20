import os
import sys
import logging
import chromadb
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

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
    try:
        embed_model = OllamaEmbedding(
            model_name="nomic-embed-text",
            base_url="http://localhost:11434",
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
        
    logger.info(f"Loading documents from folder '{data_dir}'...")
    try:
        reader = SimpleDirectoryReader(input_dir=data_dir)
        documents = reader.load_data()
        logger.info(f"Successfully loaded {len(documents)} documents.")
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
