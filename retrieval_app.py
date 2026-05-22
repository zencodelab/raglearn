import os
import sys
import logging
import chromadb
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    PromptTemplate,
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter, FilterOperator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
# Suppress noisy library logs to keep retrieval outputs clean
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Choose LLM model (can be "gemma3:4b" or "qwen2.5:7b")
LLM_MODEL = "gemma3:4b"
EMBED_MODEL = "nomic-embed-text"
DB_PATH = "./chroma_db"
COLLECTION_NAME = "local_rag_collection"

def get_query_engine(user_clearance="L2"):
    """Initializes and returns the RAG query engine connected to our local database with RBAC pre-filtering."""
    # 1. Setup local Ollama components
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = Ollama(model=LLM_MODEL, base_url=ollama_base_url, request_timeout=90.0)
    embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=ollama_base_url)
    
    Settings.llm = llm
    Settings.embed_model = embed_model
    
    # 2. Connect to existing ChromaDB
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"ChromaDB not found at {DB_PATH}. Please run ingestion.py first.")
        
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    chroma_collection = chroma_client.get_collection(name=COLLECTION_NAME)
    
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    # Load the index from the vector store
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        storage_context=storage_context
    )
    
    # 3. Define custom prompt template for secure grounding
    secure_prompt_tmpl = (
        "You are a highly secure, private government AI assistant.\n"
        "Answer the user's question ONLY using the provided source context. Do not make up facts or use external information.\n"
        "If the answer cannot be found in the context, state 'I cannot find the answer in the provided documents.'\n\n"
        "Context:\n"
        "---------------------\n"
        "{context_str}\n"
        "---------------------\n\n"
        "Question: {query_str}\n"
        "Answer:"
    )
    qa_template = PromptTemplate(secure_prompt_tmpl)
    
    # 4. Set up RBAC pre-filtering constraints
    allowed_levels = ["Public"]
    if user_clearance == "L1":
        allowed_levels = ["Public", "L1"]
    elif user_clearance == "L2":
        allowed_levels = ["Public", "L1", "L2"]
        
    logger.info(f"Applying pre-filtering: User Clearance level '{user_clearance}' allows access to {allowed_levels}")
    
    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="clearance_level",
                value=allowed_levels,
                operator=FilterOperator.IN
            )
        ]
    )
    
    # Create query engine with similarity top_k set to 3 and pre-filters active
    query_engine = index.as_query_engine(
        text_qa_template=qa_template,
        similarity_top_k=3,
        filters=filters
    )
    return query_engine

def query_rag(query_text: str, user_clearance: str = "L2"):
    """Executes the query and prints source documents alongside the response."""
    try:
        query_engine = get_query_engine(user_clearance=user_clearance)
    except Exception as e:
        print(f"\n[ERROR] Failed to initialize query engine: {e}")
        print("Please ensure Ollama is running and you have run 'ingestion.py' first.\n")
        return
        
    print(f"\n🔍 Query: \"{query_text}\"")
    print("⏳ Retrieving relevant chunks and generating response via local LLM...")
    
    # Run the query
    response = query_engine.query(query_text)
    
    # Print the synthesized answer
    print("\n==================== SYNTHESIZED RESPONSE ====================")
    print(response.response.strip())
    print("==============================================================")
    
    # Print retrieved source chunks
    print("\n📚 RETRIEVED SOURCE CONTEXT CHUNKS:")
    for i, source_node in enumerate(response.source_nodes, 1):
        metadata = source_node.node.metadata
        file_name = metadata.get("file_name", "Unknown File")
        page_label = metadata.get("page_label", None)
        score = source_node.score
        content = source_node.node.get_content().strip().replace("\n", "  ")
        
        # Limit printed chunk content length
        if len(content) > 120:
            content = content[:120] + "..."
            
        page_info = f" (Page {page_label})" if page_label else ""
        print(f"\n[{i}] Source File: {file_name}{page_info} (Relevance Score: {score:.4f})")
        print(f"    Snippet: \"{content}\"")
    print("\n" + "-"*60 + "\n")

if __name__ == "__main__":
    print(f"Using Local LLM: {LLM_MODEL} | Embedding: {EMBED_MODEL}")
    
    # If a query is provided as an argument, run it. Otherwise, enter interactive CLI loop.
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        query_rag(query)
    else:
        print("\nEntering interactive RAG CLI. Type 'exit' or 'quit' to close.")
        while True:
            try:
                user_query = input("\nAsk a question: ").strip()
                if not user_query:
                    continue
                if user_query.lower() in ["exit", "quit"]:
                    print("Exiting CLI...")
                    break
                query_rag(user_query)
            except KeyboardInterrupt:
                print("\nExiting CLI...")
                break
            except Exception as e:
                print(f"Error during query execution: {e}")
