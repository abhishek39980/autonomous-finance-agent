"""
Base tool abstractions and registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolResponse:
	success: bool
	output: Optional[Any] = None
	error: Optional[str] = None
	retry_recommended: bool = False

	def to_dict(self) -> Dict[str, Any]:
		return {
			"success": self.success,
			"output": self.output,
			"error": self.error,
			"retry_recommended": self.retry_recommended,
		}


class BaseTool:
	"""Abstract base class for tools."""

	def __init__(self, config: Any = None, llm: Any = None):
		self.config = config
		self.llm = llm

	@property
	def name(self) -> str:  # pragma: no cover - interface
		raise NotImplementedError

	@property
	def description(self) -> str:  # pragma: no cover - interface
		return ""

	def run(self, **kwargs: Any) -> ToolResponse:  # pragma: no cover - interface
		raise NotImplementedError

	def _ok(self, output: Any = None) -> ToolResponse:
		return ToolResponse(success=True, output=output)

	def _fail(self, error: str, retry_recommended: bool = False) -> ToolResponse:
		return ToolResponse(success=False, error=error, retry_recommended=retry_recommended)


class ToolRegistry:
	"""Registry that supports BaseTool instances or raw callables."""

	def __init__(self):
		self._tools: Dict[str, Callable] = {}
		self._descriptions: List[Dict[str, str]] = []

	def register(self, tool_or_name: Any, func: Optional[Callable] = None, description: str = ""):
		if isinstance(tool_or_name, BaseTool):
			name = tool_or_name.name
			func = tool_or_name.run
			description = tool_or_name.description or description
		elif isinstance(tool_or_name, str):
			name = tool_or_name
			if not callable(func):
				raise ValueError("func must be callable when registering by name")
		elif callable(tool_or_name) and func is None:
			name = tool_or_name.__name__
			func = tool_or_name
		else:
			raise ValueError("Invalid tool registration")

		self._tools[name] = func
		if not any(d["name"] == name for d in self._descriptions):
			self._descriptions.append({"name": name, "description": description})

	def has_tool(self, name: str) -> bool:
		return name in self._tools

	def get_tool(self, name: str) -> Callable:
		return self._tools[name]

	def list_tools(self) -> List[Dict[str, str]]:
		return list(self._descriptions)

	def run(self, name: str, **kwargs: Any) -> ToolResponse:
		if not self.has_tool(name):
			return ToolResponse(success=False, error=f"Unknown tool: {name}")
		tool_func = self._tools[name]
		try:
			result = tool_func(**kwargs) if kwargs else tool_func()
			if isinstance(result, ToolResponse):
				return result
			return ToolResponse(success=True, output=result)
		except Exception as e:
			return ToolResponse(success=False, error=str(e), retry_recommended=True)
