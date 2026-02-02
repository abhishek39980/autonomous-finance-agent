"""
The Main Controller.
Orchestrates the Agent's cycle: Plan -> Execute -> Evaluate.
"""

from typing import Dict, Any, List

class Controller:
    def __init__(self, config, planner, executor, evaluator, memory, tools, logger):
        self.config = config
        self.planner = planner
        self.executor = executor
        self.evaluator = evaluator
        self.memory = memory
        self.tools = tools
        self.logger = logger

    def run(self, goal: str, system_prompt: str = None, file_path: str = None) -> Dict[str, Any]:
        """
        Main execution loop.
        Returns: Dict with "success" (bool) and "output" (str).
        """
        try:
            # 1. Setup Context
            self.memory.short_term.set_goal(goal)
            if file_path:
                self.memory.short_term.set_file_path(file_path)
            
            # Log session start
            if self.logger:
                self.logger.start_session(goal)
            
            # 2. Planning Phase
            # We use the simplified getter we added to memory_manager earlier
            context = self.memory.get_context_for_goal(goal)
            
            if self.logger:
                self.logger.log_planning(goal, context, reasoning="Initial analysis.")
            
            # Ask Planner for steps
            print("\nThinking (Generating Plan)...")
            # matches the create_plan method in planner.py
            plan = self.planner.create_plan(goal, context)
            
            # Save and log the plan
            self.memory.short_term.set_plan(plan)
            if self.logger:
                self.logger.log_plan(plan)

            print(f"\nPlan Generated with {len(plan)} steps:")
            for i, step in enumerate(plan, 1):
                print(f"   {i}. {step}")

            # 3. Execution Phase
            final_output = ""
            steps_done = 0

            for i, step in enumerate(plan, 1):
                print(f"\nStep {i}: {step}")
                
                # Execute the step
                # matches the execute_step method in executor.py
                result = self.executor.execute_step(step, self.memory.get_short_term())
                
                # CRITICAL FIX: Handle Executor returning string vs dict
                if isinstance(result, str):
                    result = {"success": True, "output": result}
                elif result is None:
                    result = {"success": False, "output": "No output from tool."}

                success = result.get("success", False)
                output = result.get("output", "")
                steps_done += 1

                # Log and Memory Update
                if self.logger:
                    self.logger.log_step(i, step, "Execute", output)
                
                self.memory.short_term.add_step({
                    "step": step, 
                    "action": "Execute", 
                    "output": output, 
                    "success": success
                })

                final_output = output
                
                # Handle Step Failure
                if not success:
                    print(f"WARNING: Step failed: {output}")
                    return {
                        "success": False, 
                        "output": f"Stopped at step {i} due to error: {output}",
                        "steps_done": steps_done
                    }

            # 4. Success Return
            # This guarantees main.py receives the Dict it expects
            return {
                "success": True, 
                "output": final_output or "Task completed successfully.",
                "steps_done": steps_done
            }

        except Exception as e:
            # Catch-all to prevent main.py crashes
            if self.logger:
                self.logger.log_error("controller", e)
            
            print(f"CRITICAL Error in Controller: {e}")
            return {
                "success": False, 
                "output": f"Critical Agent Error: {str(e)}",
                "error": str(e)
            }