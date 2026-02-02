"""
Executor Module.
Parses the plan step, identifies the tool to use, and runs it.
"""

import re
from typing import Any, Dict

class Executor:
    def __init__(self, config, tools, llm, logger):
        self.config = config
        self.tools = tools  # This expects a ToolRegistry
        self.llm = llm
        self.logger = logger

    def execute_step(self, step_text: str, context: Any) -> Dict[str, Any]:
        """
        Executes a single step.
        Input: "Read the file: read_statement('data.csv')"
        Output: Dict with success/output.
        """
        try:
            # 1. Extract Tool Name and Args using Regex
            # Looks for: tool_name(arguments)
            match = re.search(r'(\w+)\((.*)\)', step_text)
            
            if not match:
                # If no tool syntax, treat as a reasoning-only step and continue
                return {
                    "success": True,
                    "output": f"Skipped non-tool step: '{step_text}'."
                }

            tool_name = match.group(1)
            raw_args = match.group(2)

            # 2. Clean Arguments
            args = []
            if raw_args:
                # Split by comma (simple parser)
                raw_arg_list = raw_args.split(',')
                for arg in raw_arg_list:
                    arg = arg.strip()
                    # Remove quotes
                    if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
                        arg = arg[1:-1]
                    # SKIP nested calls like read_statement(...) inside the args
                    if "(" in arg and ")" in arg:
                        continue 
                    args.append(arg)

            print(f"   Invoking Tool: {tool_name}")

            # 3. Check and Run Tool
            if not hasattr(self.tools, "has_tool"):
                # Fallback if tools is a list/dict instead of Registry
                return {"success": False, "output": "ToolRegistry Error: self.tools is not a valid registry."}

            if not self.tools.has_tool(tool_name):
                 return {
                    "success": False, 
                    "output": f"Tool '{tool_name}' not found."
                }

            # Get the function
            tool_func = self.tools.get_tool(tool_name)
            
            try:
                # Execute
                if args and args[0]:
                    result = tool_func(*args)
                else:
                    result = tool_func()
                
                return {"success": True, "output": str(result)}

            except Exception as tool_err:
                return {
                    "success": False, 
                    "output": f"Tool '{tool_name}' crashed: {str(tool_err)}"
                }

        except Exception as e:
            if self.logger:
                self.logger.log_error("executor", e)
            return {"success": False, "output": f"Executor Error: {str(e)}"}