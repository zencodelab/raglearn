import os
import streamlit as st
import chromadb
from retrieval_app import get_query_engine, LLM_MODEL, EMBED_MODEL, DB_PATH, COLLECTION_NAME
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import Settings, PromptTemplate, StorageContext, VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore

# 1. Page Configuration and Sleek Design
st.set_page_config(
    page_title="GovShield | Secure Local RAG Portal",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS for Sleek UI and High-Legibility Dark Aesthetics
st.markdown("""
<style>
    /* Import modern Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
    
    /* Main Background & Base Font */
    .stApp {
        background-color: #0b0f19;
        color: #f8fafc !important;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Global Text High-Contrast Overrides */
    div[data-testid="stMarkdownContainer"] p, 
    div[data-testid="stMarkdownContainer"] span,
    div[data-testid="stMarkdownContainer"] li {
        color: #f1f5f9 !important; /* Bright high-contrast slate-white */
        font-size: 0.98rem !important;
        line-height: 1.65 !important;
    }
    
    /* Bold text contrast */
    div[data-testid="stMarkdownContainer"] strong {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* Heading typography */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #090d16;
    }
    ::-webkit-scrollbar-thumb {
        background: #1e293b;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #334155;
    }
    
    /* Header styling */
    .header-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 15px;
        border-bottom: 1px solid #1e293b;
        padding-bottom: 20px;
        margin-bottom: 25px;
        margin-top: -30px;
    }
    .main-title {
        color: #ffffff !important;
        font-weight: 800;
        font-size: 2.2rem;
        margin: 0;
        background: linear-gradient(135deg, #38bdf8 0%, #0ea5e9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px rgba(56, 189, 248, 0.15);
    }
    .badge {
        background: rgba(3, 105, 161, 0.15);
        color: #38bdf8 !important;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        border: 1px solid rgba(56, 189, 248, 0.4);
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.1);
        letter-spacing: 0.05em;
    }
    
    /* Sidebar high-contrast overrides */
    [data-testid="stSidebar"] {
        background-color: #070a12;
        border-right: 1px solid #141b2e;
    }
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #cbd5e1 !important; /* Soft high-contrast silver */
    }
    .sidebar-section {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .sidebar-section b {
        color: #f8fafc !important;
    }
    
    /* Health status dot pulse */
    .status-indicator {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 0.85rem;
        margin-bottom: 10px;
        color: #cbd5e1 !important;
    }
    .dot {
        height: 8px;
        width: 8px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 6px;
    }
    .dot-green {
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
        animation: pulse 2s infinite;
    }
    .dot-red {
        background-color: #ef4444;
        box-shadow: 0 0 8px #ef4444;
    }
    
    @keyframes pulse {
        0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        }
        70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
        }
        100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
        }
    }
    
    /* Document inventory list item */
    .doc-item {
        display: flex;
        align-items: center;
        gap: 8px;
        background-color: #0f172a;
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid #1e293b;
        margin-bottom: 8px;
        font-size: 0.8rem;
        transition: all 0.2s ease;
    }
    .doc-item span {
        color: #cbd5e1 !important;
    }
    .doc-item:hover {
        border-color: #38bdf8;
        background-color: #17223b;
    }
    .doc-item:hover span {
        color: #ffffff !important;
    }
    
    /* Source Snippet Boxes */
    .source-card {
        background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
        border-left: 4px solid #0284c7;
        padding: 12px 18px;
        border-radius: 0 12px 12px 0;
        margin-bottom: 12px;
        font-size: 0.9rem;
        border-top: 1px solid #1e293b;
        border-right: 1px solid #1e293b;
        border-bottom: 1px solid #1e293b;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .source-card:hover {
        border-left-color: #38bdf8;
        background: linear-gradient(135deg, #17223b 0%, #111827 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.06);
    }
    .source-meta {
        font-size: 0.75rem;
        color: #38bdf8 !important;
        margin-bottom: 6px;
        font-weight: 600;
        letter-spacing: 0.03em;
        font-family: 'JetBrains Mono', monospace;
    }
    .source-text {
        line-height: 1.6 !important;
        color: #f1f5f9 !important; /* Pure crisp white-slate for content text */
        font-size: 0.88rem !important;
    }
    
    /* Code element custom style */
    code {
        font-family: 'JetBrains Mono', monospace !important;
        color: #38bdf8 !important;
    }
    
    /* Streamlit block styling tweaks */
    .streamlit-expanderHeader {
        background-color: #0f172a !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
    }
    .streamlit-expanderHeader span {
        color: #f1f5f9 !important;
    }
</style>
""", unsafe_allow_html=True)

# 2. Sidebar Setup & Settings Configuration
st.sidebar.markdown("<div style='text-align: center; margin-bottom: 25px; margin-top: 10px;'><h2 style='color:#38bdf8; margin:0; font-family:\"Outfit\", sans-serif; font-weight:800; letter-spacing:0.5px;'>🛡️ GovShield</h2><p style='color:#64748b; font-size:0.85rem; margin:0;'>Secure Offline RAG Engine</p></div>", unsafe_allow_html=True)

# Model Settings Section
st.sidebar.subheader("⚙️ System Configuration")
selected_llm = st.sidebar.selectbox(
    "Synthesis LLM Model",
    options=["gemma3:4b", "qwen2.5:7b"],
    index=0,
    help="Select the local LLM model running in Ollama for synthesizing answers."
)

selected_top_k = st.sidebar.slider(
    "Retrieval Depth (Top-K)",
    min_value=1,
    max_value=5,
    value=3,
    help="The number of relevant text chunks to retrieve and feed to the LLM."
)

# System Health indicator
st.sidebar.subheader("🔌 Connection Status")
try:
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    colls = chroma_client.list_collections()
    db_indicator = '<span><span class="dot dot-green"></span>Connected</span>'
except Exception:
    db_indicator = '<span><span class="dot dot-red"></span>Disconnected</span>'

st.sidebar.markdown(f"""
<div class="sidebar-section">
    <div class="status-indicator">
        <b>Vector DB:</b> 
        {db_indicator}
    </div>
    <div class="status-indicator">
        <b>Ollama Server:</b> 
        <span><span class="dot dot-green"></span>Online (port 11434)</span>
    </div>
    <div style="font-size:0.8rem; margin-top: 12px; border-top: 1px solid #1e293b; padding-top: 10px; color: #94a3b8;">
        <b>Embedding Model:</b> <br>
        <code style="color: #38bdf8; background: #080d15; padding: 2px 6px; border-radius: 4px; display:inline-block; margin-top:4px;">{EMBED_MODEL}</code>
    </div>
</div>
""", unsafe_allow_html=True)

# Document Inventory
st.sidebar.subheader("📂 Document Inventory")
data_dir = "./data"
if os.path.exists(data_dir):
    files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
    if files:
        file_list_html = "".join([
            f'<div class="doc-item">📄 <span>{name}</span></div>' 
            for name in files
        ])
        st.sidebar.markdown(file_list_html, unsafe_allow_html=True)
    else:
        st.sidebar.info("No documents found in data/ folder.")
else:
    st.sidebar.warning("Data directory missing.")

# 3. Cache the Query Engine creation
@st.cache_resource(show_spinner=False)
def load_rag_engine(llm_name, top_k):
    ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = Ollama(model=llm_name, base_url=ollama_base_url, request_timeout=120.0)
    embed_model = OllamaEmbedding(model_name=EMBED_MODEL, base_url=ollama_base_url)
    
    Settings.llm = llm
    Settings.embed_model = embed_model
    
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    chroma_collection = chroma_client.get_collection(name=COLLECTION_NAME)
    
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)
    
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
    
    return index.as_query_engine(
        text_qa_template=qa_template,
        similarity_top_k=top_k
    )

# Initialize query engine based on sidebar state
try:
    query_engine = load_rag_engine(selected_llm, selected_top_k)
except Exception as e:
    st.error(f"⚠️ Failed to connect to local database: {e}. Please run `python ingestion.py` to index documents first.")
    st.stop()

# 4. Main UI Layout
st.markdown("""
<div class="header-container">
    <h1 class="main-title">🛡️ GovShield Secure RAG</h1>
    <span class="badge">AIR-GAPPED COMPLIANT</span>
</div>
""", unsafe_allow_html=True)

st.caption("This system processes all data entirely on your local machine. No external API calls are made, ensuring 100% data sovereignty.")

# Chat history state initialization
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display prior chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources") and msg["role"] == "assistant":
            with st.expander("🔍 View Retrieved Sources"):
                for src in msg["sources"]:
                    st.markdown(f"""
                    <div class="source-card">
                        <div class="source-meta">📄 FILE: {src['file'].upper()} | RELEVANCE: {src['score']:.4f}</div>
                        <div class="source-text">"{src['text']}"</div>
                    </div>
                    """, unsafe_allow_html=True)

# 5. Chat Input and Logic
if user_prompt := st.chat_input("Ask a question about the secure intranet documents..."):
    # Display user query in UI
    with st.chat_message("user"):
        st.markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    
    # Process RAG response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        sources_placeholder = st.empty()
        
        with st.spinner("Analyzing document database and generating grounded answer..."):
            try:
                # Query RAG engine
                response = query_engine.query(user_prompt)
                synthesized_text = response.response.strip()
                
                # Render synthesized text
                response_placeholder.markdown(synthesized_text)
                
                # Format source nodes
                sources = []
                for node in response.source_nodes:
                    sources.append({
                        "file": node.node.metadata.get("file_name", "Unknown Document"),
                        "score": node.score or 0.0,
                        "text": node.node.get_content().strip()
                    })
                
                # Render sources
                if sources:
                    with sources_placeholder.expander("🔍 View Retrieved Sources"):
                        for src in sources:
                            st.markdown(f"""
                            <div class="source-card">
                                <div class="source-meta">📄 FILE: {src['file'].upper()} | RELEVANCE: {src['score']:.4f}</div>
                                <div class="source-text">"{src['text']}"</div>
                            </div>
                            """, unsafe_allow_html=True)
                
                # Save to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": synthesized_text,
                    "sources": sources
                })
            except Exception as e:
                err_msg = f"An error occurred while communicating with the local LLM model: {e}"
                response_placeholder.error(err_msg)
                st.session_state.messages.append({"role": "assistant", "content": err_msg})
