# Autonomous Finance-agent (Local RAG Application)

This is a **100% Local Document Q&A Knowledge Base** built using **LlamaIndex** and **Streamlit**. 

It allows you to upload any PDF or TXT files, automatically parses and chunks the text, creates vector embeddings using HuggingFace models, and lets you interrogate the documents through an interactive chat interface. 

Crucially, **no data ever leaves your machine.** The application uses local vector storage (`FAISS`/`SimpleVectorStore`) and routes all conversational LLM queries to a local server like **LM Studio** or **Ollama**.

---

## 🚀 Features
- **Upload Multiple Documents:** Drag and drop PDFs and text files directly into the UI.
- **Local Embeddings:** Uses `sentence-transformers/all-MiniLM-L6-v2` down-loaded locally via HuggingFace for rapid, private vectorization.
- **Local AI Chat:** Chat with your documents using models running on your own GPU via LM Studio (ex: Mistral, Llama-3).
- **Persistent Storage:** Embeddings are saved to a `./storage` directory so you don't have to re-process the exact same files every time you boot up.
- **Context-Aware:** The AI reliably cites and answers based *only* on the chunks and context of the documents you provide.

---

## 🛠️ Tech Stack
- **Frontend:** Streamlit (`app.py`)
- **Core Orchestrator:** LlamaIndex
- **Vector Database:** SimpleVectorStore (LlamaIndex Native)
- **Embeddings:** HuggingFace `sentence-transformers`
- **Local LLM Engine:** LM Studio (or any OpenAI-compatible localhost endpoint)
- **Language:** Python 3.x

---

## ⚙️ How to Install & Run Locally

### 1. Prerequisites
You must have Python installed. You also need a local LLM server running.
- Download and install [LM Studio](https://lmstudio.ai/).
- Open LM Studio, search for a model (like `Mistral-7B-Instruct`), and download it.
- Go to the **Local Server** `< >` tab in LM Studio, select your model, and hit **Start Server** on Port `1234`.

### 2. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/document-qa-system.git
cd document-qa-system
```

### 3. Set Up Virtual Environment (Recommended but Optional)
```bash
python -m venv .venv
# Activate on Windows:
.\.venv\Scripts\activate
# Activate on Mac/Linux:
source .venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the Application
```bash
streamlit run app.py
```
This will automatically open your browser to `http://localhost:8501`.

---

## 📝 Configuration (`config.yaml`)

You can change models and settings without touching the code. Edit the `config.yaml` file to point to different Localhost endpoints or tweak the retrieval logic:

```yaml
llm:
  provider: "ollama"  
  base_url: "http://localhost:1234/v1" # Point this exactly to LM Studio
  temperature: 0.1 # Keep low for strict analytical answers
```

*(Note: The system dynamically scales to whatever specific model is currently physically loaded into LM Studio's RAM).*
