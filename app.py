import os
import tempfile
import streamlit as st
from pathlib import Path
import yaml

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    StorageContext,
    load_index_from_storage
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.llms import CustomLLM, CompletionResponse, CompletionResponseGen, LLMMetadata
from typing import Any
import requests

class LMStudioLLM(CustomLLM):
    base_url: str = "http://localhost:1234/v1"
    model_name: str = "local-model"
    temperature: float = 0.1

    @property
    def metadata(self) -> LLMMetadata:
        # Provide basic metadata so LlamaIndex knows how to chunk/allocate tokens
        return LLMMetadata(model_name=self.model_name, context_window=4096, num_output=1000)

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        # LlamaIndex will format its system prompts and context into this single `prompt` string.
        # We then forcefully send it as an exclusive "user" role, completely avoiding Jinja errors
        # in LM Studio for models that don't support "system" roles.
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "stream": False
        }
        # Increased timeout to 600 seconds for slower local GPU generation
        res = requests.post(url, json=payload, timeout=600)
        res.raise_for_status()
        return CompletionResponse(text=res.json()["choices"][0]["message"]["content"])

    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        raise NotImplementedError()

# Configure LlamaIndex Settings globally
@st.cache_resource
def configure_settings():
    def local_load():
        import yaml
        from pathlib import Path
        local_root = Path(__file__).resolve().parent
        with open(local_root / "config.yaml", "r") as f:
            return yaml.safe_load(f)

    # Load config inside the cached function exactly once
    cfg = local_load()
    api_url = cfg.get("llm", {}).get("base_url", "http://localhost:1234/v1")
    temp = float(cfg.get("llm", {}).get("temperature", 0.1))
    embed_id = cfg.get("embeddings", {}).get("model_id", "sentence-transformers/all-MiniLM-L6-v2")

    # Use our custom wrapper instead of the strict OpenAI client
    Settings.llm = LMStudioLLM(
        base_url=api_url,
        model_name="local-model",
        temperature=temp
    )
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=embed_id
    )
    Settings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

configure_settings()

def get_index():
    storage_dir = "./storage"
    if os.path.exists(storage_dir) and os.listdir(storage_dir):
        # Load the existing index
        storage_context = StorageContext.from_defaults(persist_dir=storage_dir)
        return load_index_from_storage(storage_context)
    return None

st.set_page_config(page_title="V", page_icon="static/logo.png" if os.path.exists("static/logo.png") else "V", layout="wide")

if os.path.exists("static/logo.png"):
    st.image("static/logo.png", width=400)
st.markdown("Upload your PDFs and chat with them using local LLMs configured in `config.yaml`.")

# Sidebar for uploading documents
with st.sidebar:
    st.header("1. Document Upload")
    uploaded_files = st.file_uploader(
        "Upload PDF or TXT files", type=["pdf", "txt"], accept_multiple_files=True
    )
    
    if st.button("Process Documents"):
        if uploaded_files:
            with st.spinner("Processing documents and building embeddings..."):
                # Save uploaded files temporarily
                with tempfile.TemporaryDirectory() as temp_dir:
                    for uploaded_file in uploaded_files:
                        temp_path = os.path.join(temp_dir, uploaded_file.name)
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    
                    # Read documents
                    documents = SimpleDirectoryReader(temp_dir).load_data()
                    
                    # Create new index and persist it natively (SimpleVectorStore)
                    index = VectorStoreIndex.from_documents(documents)
                    index.storage_context.persist(persist_dir="./storage")
                    
                    st.session_state["index_ready"] = True
                st.success(f"Successfully processed and embedded {len(uploaded_files)} files!")
        else:
            st.warning("Please upload files first.")

st.divider()

# Chat Interface
st.header("2. Chat Interface")
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask a question about your documents..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        index = get_index()
        if not index:
            st.info("No documents found in the database. Please upload and process documents first.")
        else:
            try:
                query_engine = index.as_query_engine()
                with st.spinner("Retrieving context and thinking..."):
                     response = query_engine.query(prompt)
                     st.write(response.response)
                     st.session_state.messages.append({"role": "assistant", "content": response.response})
            except Exception as e:
                st.error(f"Error querying index: {e}")
