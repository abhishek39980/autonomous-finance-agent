"""
Offline Wealth Manager — Main Entry.
"""
import argparse
import sys
import re
from pathlib import Path
import requests

# Add root to path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.config import load_config
from agent.controller import Controller
from agent.executor import Executor
from agent.logger import AgentLogger
from agent.planner import Planner
from agent.llm_client import LLMClient
from memory.memory_manager import MemoryManager
from tools import get_default_tools
from tools.finance_tools import GLOBAL_STATE

DEFAULT_SYSTEM_PROMPT = (
    "You are a private financial auditor. Your goal is to analyze bank statements locally. "
    "Use the finance tool: read_statement(file_path), then categorize_transactions(), then generate_dashboard(), and finally save_memory()."
)

def run_agent(goal: str, config_path: Path | None = None, file_path: Path | None = None, pdf_password: str | None = None) -> dict:
    config = load_config(config_path or ROOT / "config.yaml")
    logger = AgentLogger(config.logging.dir, config.logging.level)

    # 1. Check LLM Connection
    try:
        base_url = config.llm.base_url.rstrip('/')
        is_ollama = "11434" in base_url
        check_url = f"{base_url}/api/tags" if is_ollama else f"{base_url}/models"
        resp = requests.get(check_url, timeout=5)
        if resp.status_code not in (200, 404):   # 404 is ok for some LM Studio versions
            raise ConnectionError(f"Server responded with {resp.status_code}")
    except requests.exceptions.ConnectionError:
        provider = "Ollama" if is_ollama else "LM Studio"
        logger.log_error("main", f"LLM not reachable at {base_url}")
        return {"success": False, "error": f"{provider} is not running. Please start it first.", "llm_not_running": True}
    except Exception as e:
        logger.log_error("main", f"LLM check error: {e}")
        return {"success": False, "error": f"LLM Connection Failed: {e}", "llm_not_running": True}

    # 2. Initialize Components
    try:
        llm = LLMClient(config.llm)
        
        # --- CRITICAL FIX: Load Tools and Verify Registry ---
        tools = get_default_tools()
        
        # Debug Print: Verify tools are loaded correctly
        if hasattr(tools, "list_tools"):
            print(f"Tools Loaded: {[t['name'] for t in tools.list_tools()]}")
        else:
            print(f"CRITICAL ERROR: 'tools' is {type(tools)}, expected ToolRegistry.")
            return {"success": False, "error": "ToolRegistry failed to load."}
        # ----------------------------------------------------

        memory_manager = MemoryManager(config, logger=logger)
        if file_path:
            memory_manager.short_term.set_file_path(str(file_path))
            print(f"Target File Set: {file_path}")

        # Store PDF password in shared state so read_statement() can use it
        if pdf_password:
            GLOBAL_STATE["pdf_password"] = pdf_password
            print("PDF password stored for decryption.")

        planner = Planner(config, llm, logger)
        executor = Executor(config, tools, llm, logger)
        # We use a dummy evaluator for this lightweight version
        evaluator = None 
        
        controller = Controller(
            config, planner, executor, evaluator, memory_manager, tools, logger
        )

        return controller.run(goal, system_prompt=DEFAULT_SYSTEM_PROMPT, file_path=str(file_path) if file_path else None)

    except Exception as e:
        logger.log_error("run_agent", e)
        return {"success": False, "error": str(e)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("goal", nargs="?", help="The main task")
    parser.add_argument("--file", "-f", type=Path, default=None, help="Path to CSV")
    args = parser.parse_args()

    goal = (args.goal or "").strip()
    if args.file and not goal:
        goal = f"Analyze the financial statement at {args.file}, generate a detailed wealth report dashboard, and save the analysis to memory."

    if not goal:
        print("Error: Please provide a goal or a file.")
        print("Usage: python main.py --file dummy_statement.csv")
        return

    print(f"Starting Agent with goal: \"{goal}\"")
    result = run_agent(goal, file_path=args.file)

    if result.get("success"):
        print("\nExecution Finished Successfully!")
    else:
        print(f"\nExecution Failed: {result.get('error')}")
        if result.get("output"):
            print(f"Details: {result.get('output')}")

if __name__ == "__main__":
    main()