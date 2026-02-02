"""
Structured JSONL logging for the agent.
"""

import json
import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

class AgentLogger:
    def __init__(self, log_dir: str, level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.level = level
        self.log_file = self.log_dir / f"agent_{datetime.datetime.now().strftime('%Y-%m-%d')}.jsonl"

    def _write(self, entry: Dict[str, Any]):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"⚠️ Logger failed to write to file: {e}")

    def start_session(self, goal: str):
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "session_start",
            "goal": goal
        }
        self._write(entry)

    def log(self, component: str, message: str, context: Optional[Dict[str, Any]] = None):
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "info",
            "component": component,
            "message": message,
            "context": context or {}
        }
        self._write(entry)

    def log_error(self, component: str, error: Any, context: Optional[Dict[str, Any]] = None):
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "error",
            "component": component,
            "error": str(error),
            "context": context or {}
        }
        print(json.dumps(entry)) 
        self._write(entry)

    def log_rejection(self, reason: str, goal_snippet: str):
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "rejection",
            "reason": reason,
            "goal_snippet": goal_snippet
        }
        self._write(entry)

    # --- FIX: Added 'reasoning' argument here ---
    def log_planning(self, goal: str, context: str, reasoning: str = ""):
        """Log the start of the planning phase."""
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "planning_start",
            "goal": goal,
            "context_summary": context[:200] + "..." if len(context) > 200 else context,
            "reasoning": reasoning
        }
        self._write(entry)
    # --------------------------------------------

    def log_plan(self, plan: List[str]):
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "plan_created",
            "plan": plan
        }
        self._write(entry)

    def log_step(self, step_number: int, thought: str, action: str, tool_input: str):
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "step",
            "step": step_number,
            "thought": thought,
            "action": action,
            "tool_input": tool_input
        }
        self._write(entry)

    def log_tool_result(self, step_number: int, tool_name: str, output: str, success: bool):
        safe_output = str(output)
        entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": "tool_result",
            "step": step_number,
            "tool": tool_name,
            "success": success,
            "output": safe_output[:1000] + "..." if len(safe_output) > 1000 else safe_output
        }
        self._write(entry)