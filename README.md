# 🤖 Autonomous Finance Agent

A lightweight autonomous agent that analyzes bank statements and generates financial dashboards.

## Features

- 📄 PDF bank statement parsing
- 🏷️ Automatic transaction categorization
- 📊 Interactive HTML dashboard generation
- 🤖 LLM-powered autonomous execution

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Agent

```bash
python main.py --file bankstatement.pdf
```

The agent will:
1. Parse your PDF
2. Extract and categorize transactions
3. Generate an HTML dashboard
4. Open it in your browser

## Configuration

Edit `config.yaml` to customize LLM settings:

```yaml
llm:
  provider: "ollama"      # or "lm_studio"
  model_id: "llama2"
  base_url: "http://localhost:11434"
```

## Project Structure

```
autonomous-agent/
├── main.py              # Entry point
├── config.yaml          # Configuration
├── requirements.txt     # Dependencies
├── agent/               # Agent core
│   ├── controller.py    # Main orchestrator
│   ├── planner.py       # Task planning
│   ├── executor.py      # Task execution
│   └── llm_client.py    # LLM interface
├── tools/               # Agent tools
│   └── finance_tools.py # PDF parsing & categorization
├── data/                # Data files
├── reports/             # Generated dashboards
├── logs/                # Execution logs
└── memory/              # Agent memory
```

## How It Works

1. **You provide a goal** - e.g., "Analyze my bank statement"
2. **Agent plans** - Breaks down into steps
3. **Agent executes** - Uses tools to complete tasks
4. **Dashboard generated** - Beautiful HTML report

## Dashboard Features

- 💰 Income and expense summary
- 📈 Category breakdown (pie chart)
- 📉 Top spending categories (bar chart)
- 📋 Detailed transaction table
- 🎨 Dark theme UI

## Troubleshooting

**"LLM Connection Failed"**
- Start Ollama: `ollama serve`
- Or use LM Studio

**"No transactions found"**
- Ensure PDF is a valid bank statement
- Check PDF format compatibility

**"Module not found"**
- Install dependencies: `pip install -r requirements.txt`

## License

MIT
