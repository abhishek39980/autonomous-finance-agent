

<div align="center">


# 💰 Autonomous Finance Agent

### An intelligent, **100% offline** bank statement analyzer powered by local LLMs.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.31%2B-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![LM Studio](https://img.shields.io/badge/Local%20LLM-LM%20Studio%20%7C%20Ollama-8B5CF6?style=flat)](https://lmstudio.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat)](LICENSE)

> **Your financial data never leaves your machine.** No cloud APIs. No subscription fees. No data leaks.

![Demo GIF](docs/demo.gif)
<!-- 📹 Replace the path above once you record a screen capture of the app running -->

</div>

---

## ✨ Why I Built This

Most financial dashboards require you to **upload sensitive bank statements to a third-party server**. That's a non-starter for privacy-conscious users.

This project proves you can have **AI-powered financial intelligence without sacrificing data privacy**:

- 🔒 **100% Offline** — Every LLM inference runs locally via [LM Studio](https://lmstudio.ai) or [Ollama](https://ollama.ai). Zero cloud calls.
- 🗄️ **Local SQLite Database** — Transactions are durably stored locally for instant aggregations and lightning-fast historical queries.
- 🧠 **FAISS Semantic Search** — Ask complex questions ("Where did I eat last month?") using locally-embedded transaction data powered by `SentenceTransformers`.
- 🔮 **Predictive Analytics** — Uses Scikit-Learn to detect recurring subscriptions and forecast next month's spending.
- 📄 **PDF Decryption** — Handles password-protected bank statement PDFs (common in India) natively.
- 🧹 **Indian UPI Cleaning** — Custom regex logic strips alphanumeric noise from UPI strings into readable labels.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        User (Browser / CLI)                      │
└─────────────────────────────┬────────────────────────────────────┘
                              │  Upload PDF / CSV / Excel
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│              Streamlit UI  (bank_app.py)                         │
│    ┌─────────────┐   ┌──────────────────┐   ┌───────────────┐   │
│    │  File Upload │   │  PDF Decryption  │   │  AI Chat Tab  │   │
│    └──────┬──────┘   └────────┬─────────┘   └───────┬───────┘   │
└───────────┼───────────────────┼─────────────────────┼───────────┘
            │                   │                      │
            ▼                   ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│              Agent Pipeline  (main.py → agent/controller.py)     │
│                                                                  │
│   read_statement → clean_upi → categorize → generate_dashboard  │
│                                    ↕                             │
│                         save_memory / recall                     │
└─────────────────────────────┬────────────────────────────────────┘
                              │
            ┌─────────────────┼──────────────────────┐
            ▼                 ▼                       ▼
┌─────────────────┐  ┌────────────────┐  ┌───────────────────────┐
│  Local LLM      │  │  Pandas / Data │  │  Local Memory Store   │
│  (LM Studio /  │  │  Processing    │  │  (data/memory.json)   │
│   Ollama)      │  │  (finance_     │  │                       │
│  port 1234 /   │  │   tools.py)    │  │  Recurring Detection  │
│  port 11434    │  │                │  │  Trend Analysis       │
└─────────────────┘  └───────┬────────┘  └───────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   HTML Dashboard         │
              │   (reports/dashboard.html│
              │    powered by Chart.js)  │
              └──────────────────────────┘
```

**Data Flow:** `PDF/CSV → Text Extraction → UPI Cleaning → Local LLM Categorization → Local Memory → Interactive HTML Dashboard`

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **UI** | [Streamlit](https://streamlit.io) | Interactive web dashboard with 5 tabs |
| **Local LLM** | [LM Studio](https://lmstudio.ai) / [Ollama](https://ollama.ai) | 100% offline AI inference |
| **Data** | [Pandas](https://pandas.pydata.org) & [SQLite](https://sqlite.org/) | Transaction processing and persistent storage |
| **Vector DB** | [FAISS](https://faiss.ai/) & `SentenceTransformers` | Fast offline semantic transaction search |
| **Analytics** | [Scikit-Learn](https://scikit-learn.org/) | Time-series forecasting and anomaly detection |
| **PDF** | [pdfplumber](https://github.com/jsvine/pdfplumber) + PyMuPDF | PDF & encrypted PDF parsing |
| **Charts** | [Chart.js](https://www.chartjs.org) | Interactive financial charts |
| **Config** | YAML | Model swap without code changes |

---

## 📂 Project Structure

```
autonomous-agent/
│
├── bank_app.py              ← Main Streamlit app (entry point)
├── main.py                  ← Agent pipeline runner
├── config.yaml              ← LLM config (model, port, temperature)
├── requirements.txt         ← Python dependencies
├── run.bat                  ← One-click Windows launcher
│
├── agent/                   ← Core agent logic
│   ├── config.py            ←   Config dataclasses & YAML loader
│   ├── controller.py        ←   Orchestrates tool calls
│   ├── llm_client.py        ←   Local LLM connector (LM Studio / Ollama)
│   ├── planner.py           ←   Goal → step decomposition
│   ├── executor.py          ←   Executes individual tool steps
│   └── logger.py            ←   Structured JSONL logging
│
├── analysis/                ← Pandas-based financial logic
│   ├── forecasting.py       ←   Scikit-Learn linear regression forecast
│   ├── insights_engine.py   ←   Month-over-month trends & spending spikes
│   └── recurring_detector.py←   Identifies subscriptions via std dev logic
│
├── database/                ← SQLite storage layer
│   ├── db_manager.py        ←   SQLAlchemy engine setup
│   ├── models.py            ←   ORM: Transactions, Insights, Recurring
│   └── queries.py           ←   Aggregation and retrieval helpers
│
├── vector_store/            ← Semantic search layer
│   ├── embedding_model.py   ←   Local SentenceTransformer model
│   ├── faiss_index.py       ←   FAISS index wrapper
│   └── semantic_search.py   ←   Search orchestration logic
│
├── tools/                   ← Finance processing tools
│   ├── finance_tools.py     ←   Core: read, category, dashboard, save_memory
│   └── pdf_tools.py         ←   PDF + encrypted PDF extraction
│
├── data/                    ← Runtime data (gitignored)
│   ├── finance.db           ←   SQLite database file
│   └── vector_index.faiss   ←   FAISS semantic embeddings vector store
│
├── reports/                 ← Generated HTML dashboards
│   └── dashboard.html       ←   Latest dashboard output
│
├── static/                  ← Offline JS assets
│   └── chart.min.js         ←   Chart.js bundled locally (no CDN)
│
└── sample_output/           ← Pre-generated demo artifacts
    ├── dummy_statement.csv  ←   Realistic sample data
    ├── dashboard.html       ←   Live-preview dashboard (open in browser!)
    └── generate_samples.py  ←   Regenerate sample data
```

---

## ⚡ Quick Start

### 1. Prerequisites

- **Python 3.10+**
- **[LM Studio](https://lmstudio.ai)** (recommended) — Download a model (e.g. `mistral-7b-instruct`) and start the local server on port `1234`.
  
  *OR*
  
- **[Ollama](https://ollama.ai)** — Run `ollama run mistral` and it auto-serves on port `11434`.

### 2. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/autonomous-finance-agent.git
cd autonomous-finance-agent

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure the LLM

Edit `config.yaml` to match your setup:

```yaml
llm:
  provider: lmstudio          # or "ollama"
  model_id: mistral-7b-instruct-v0.1
  base_url: http://localhost:1234/v1   # LM Studio default
  # base_url: http://localhost:11434   # Ollama default
```

### 4. Run

```bash
# Windows — double-click run.bat, or:
streamlit run bank_app.py

# The app opens at http://localhost:8501
```

### 5. Try It Instantly (No LLM needed)

Open `sample_output/dashboard.html` directly in your browser to see the pre-generated interactive dashboard.

---

## 🔐 PDF Password Support

If your bank issues **encrypted / password-protected PDF statements** (common with Indian banks like HDFC, SBI, ICICI), simply enter the password in the **sidebar** before uploading. The app decrypts the PDF locally — your password is never stored or transmitted.

---

## 🧠 Key Features

- **Semantic Search (RAG)** — Uses FAISS and `sentence-transformers` for powerful, context-aware querying against transaction history ("Did I pay Netflix?").
- **Financial Forecasting** — Linear regression models project estimated expenses for upcoming months.
- **AI Insights Engine** — Automatically generates text insights (spending spikes, merchant concentration, MoM growth) using local Pandas aggregations.
- **Recurring Payment Detection** — Spots hidden subscriptions via statistical interval variance analysis.
- **UPI Transaction Cleaning** — Regex pipeline strips transaction IDs and UPI noise. `UPI/CR/123456/ZOMATO...` → `Zomato`
- **Auto-Categorization** — Auto-assigns categories like Food, Travel, Shopping, Bills, or Entertainment natively.
- **5 Premium UI Tabs** — An elegant Streamlit interface presenting Dashboard, Insights, Recurring Payments, Forecast, and AI Chat windows.

---

## 📸 Sample Output

| Dashboard | Chat Interface |
|---|---|
| *See `sample_output/dashboard.html`* | *Run the app and analyze any CSV* |

---

## 🤝 Contributing

Pull requests welcome! Please open an issue first for major changes.

---

<div align="center">

Built with ❤️ for privacy-first personal finance · **No cloud. No compromise.**

</div>
