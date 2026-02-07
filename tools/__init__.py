"""
Tool abstraction layer. Modular, extensible tools with unified response format.
"""

from .base_tool import BaseTool, ToolResponse, ToolRegistry
from .default_tools import SearchTool, FileTool, CalculatorTool
from .code_tool import CodeExecutionTool
try:
    from .finance_tools import read_statement, categorize_transactions, generate_dashboard, save_memory
except Exception as e:
    error_msg = str(e)
    def _finance_tools_unavailable(*_args, **_kwargs):
        return f"Finance tools unavailable: {error_msg}"

    read_statement = _finance_tools_unavailable
    categorize_transactions = _finance_tools_unavailable
    generate_dashboard = _finance_tools_unavailable
    save_memory = _finance_tools_unavailable
    save_memory = _finance_tools_unavailable

__all__ = [
    "BaseTool",
    "ToolResponse",
    "ToolRegistry",
    "SearchTool",
    "FileTool",
    "CodeExecutionTool",
    "CalculatorTool",
    "read_statement",
    "categorize_transactions",
    "generate_dashboard",
    "save_memory",
]


def get_default_tools(config=None, llm=None):
    """Return registry with all default tools. Config optional for timeouts; llm reserved for future use."""
    registry = ToolRegistry()
    registry.register(SearchTool(config))
    registry.register(FileTool(config))
    registry.register(CodeExecutionTool(config))
    registry.register(CalculatorTool(config))
    registry.register("read_statement", read_statement, "Read a bank statement file (CSV/XLSX/PDF).")
    registry.register("categorize_transactions", categorize_transactions, "Categorize transactions in the loaded statement.")
    registry.register("generate_dashboard", generate_dashboard, "Generate an HTML dashboard from loaded data.")
    registry.register("save_memory", save_memory, "Save analysis results to persistent memory.")
    return registry
