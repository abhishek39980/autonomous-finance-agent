"""
Planner Module.
Generates a step-by-step plan using the LLM.
"""

from typing import List

class Planner:
    def __init__(self, config, llm, logger):
        self.config = config
        self.llm = llm
        self.logger = logger

    def create_plan(self, goal: str, context: str) -> List[str]:
        """
        Ask LLM to break the goal into steps.
        Returns: List[str]
        """
        # System prompt to guide the LLM's behavior
        system_prompt = (
            "You are a strategic planner. "
            "Break the user's goal into 3-5 clear, executable steps for a financial auditor agent. "
            "Return ONLY the steps as a numbered list. "
            "The available tools are: read_statement(file_path), categorize_transactions(), generate_dashboard()."
        )
        
        # User prompt with the specific goal
        prompt = f"Goal: {goal}\nContext: {context}\n\nPlan:"
        
        try:
            # use .complete() to get the raw text response
            response = self.llm.complete(prompt, system=system_prompt)
            
            # Parse the response text into a clean list of strings
            steps = []
            for line in response.splitlines():
                line = line.strip()
                # Remove numbering (e.g., "1. " or "- ") to get just the instruction
                if line and (line[0].isdigit() or line.startswith("-")):
                    # extensive strip to remove "1.", "1)", "-", etc.
                    clean_line = line.lstrip("0123456789.-) ").strip()
                    if clean_line:
                        steps.append(clean_line)
            
            # Fallback: If LLM returned no valid steps, just return the goal as a single step
            if not steps:
                return [f"Execute the goal: {goal}"]
                
            return steps

        except Exception as e:
            # Log the error if possible, otherwise just return a safe fallback
            if self.logger:
                self.logger.log_error("planner", e)
            return [f"Execute goal: {goal}"]