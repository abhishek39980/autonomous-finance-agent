# 🤖 Autonomous Finance Agent

A lightweight, autonomous AI agent that analyzes bank statements, categorizes transactions, and generates insightful financial dashboards. It runs entirely locally on your machine.

> **Tested Environment:** running `mistral-7b-instruct-v0.2` via **LM Studio**.

## ✨ Features

### 📄 Advanced PDF Parsing
- **Intelligent Text-Stream Strategy**: Handles complex "open" table layouts (like Standard Chartered statements) without relying on grid lines.
- **Smart Logic**: Automatically detects multi-line descriptions and merges them correctly.
- **Robust Regex**: Supports various date formats (e.g., `DD Mon YY`, `DD/MM/YYYY`) and amount formats with `Dr`/`Cr` suffixes.

### 🧠 Intelligent Analysis
- **Auto-Categorization**: Automatically categorizes transactions into `Food`, `Travel`, `Shopping`, `UPI`, `Bills`, etc. based on description keywords.
- **Recurring Transaction Detection**: Identifies subscriptions and monthly bills stored in persistent memory.
- **Spending Trends**: Compares current spending against historical averages.

### 📊 Premium Dashboard
- **Rich HTML Report**: Generates a `dashboard.html` file with:
    - 💰 Income vs. Spending Summary
    - 🍩 Interactive Category Doughnut Chart
    - 📊 Category Breakdown Bar Chart
    - 🔥 Top Expenses List
    - 📋 Full Searchable Transaction Table
    - 🎨 Modern "Pitch Black" UI with Neon Accents

### 💾 Persistent Memory
- Saves transaction history and insights to `data/memory.json`.
- Learns over time to provide better trend analysis.

---

## 🚀 Step-by-Step Guide

### prerequisites
1.  **Python 3.10+** installed.
2.  **LM Studio** installed (or Ollama/LocalAI).
3.  **Mistral 7B Instruct** model loaded.

### 1. Setup LM Studio (Recommended)
This agent relies on a local LLM for decision making.
1.  Download & Install [LM Studio](https://lmstudio.ai/).
2.  Search for `mistral-7b-instruct-v0.2`.
3.  Download a quantized version (e.g., `Q4_K_M`).
4.  Go to the **"Local Server"** tab (double arrow icon).
5.  Select the model from the dropdown.
6.  Start the server (usually on port `1234`).
    *   Ensure "Cross-Origin-Resource-Sharing (CORS)" is enabled (default on).

### 2. Install Dependencies
Open your terminal in the project folder:

```bash
pip install -r requirements.txt
```

*Note: You might need to install `pdfplumber` separately if it's not in the requirements yet:*
```bash
pip install pdfplumber pandas requests pyyaml chromadb
```

### 3. Configure the Agent
Open `config.yaml` and ensure it points to your local server:

```yaml
llm:
  provider: "ollama" # (Keep as is, works with LM Studio generic API)
  base_url: "http://localhost:1234/v1" # Point to LM Studio
  model_id: "mistral-7b-instruct-v0.2" # Optional, for logging
```

### 4. Run the Agent
Place your bank statement (e.g., `statement.pdf`) in the project folder.

**Command:**
```bash
python main.py --file statement.pdf
```

**What happens next:**
1.  The agent reads the PDF using its custom parsing tool.
2.  It categorizes every transaction.
3.  It generates a `dashboard.html` in the `reports/` folder.
4.  It saves insights to `data/memory.json`.
5.  It automatically opens the dashboard in your default browser.

---

## 📂 Project Structure

```
autonomous-agent/
├── main.py              # 🚀 Entry point
├── config.yaml          # ⚙️ Configuration
├── requirements.txt     # 📦 Dependencies
├── agent/               # 🧠 Brain (Planner, Executor, Logic)
├── tools/               # 🛠️ Tools
│   ├── pdf_tools.py     # 📄 Advanced PDF Parsing Logic
│   └── finance_tools.py # 💰 Finance Calculations & Dashboard Gen
├── data/                # 💾 Persistent Memory & Storage
├── reports/             # 📊 Generated HTML Dashboards
└── logs/                # 📝 Execution Logs
```

## 🛠️ Troubleshooting

**"LLM Connection Failed"**
- Check if LM Studio server is running (Green light).
- Verify the port in `config.yaml` matches LM Studio (default `1234`).

**"No transactions found"**
- Ensure the PDF is a text-based bank statement, not a scanned image.
- The parser is optimized for standard layouts; complex custom tables might need specific tweaking in `pdf_tools.py`.

**"Empty Charts"**
- Analyze the `test_pdf_parsing.py` output to see if amounts are being extracted as positive numbers (Deposits) instead of negative (Withdrawals). The agent logic expects **negatives** for spending.

## 📜 License
MIT License
