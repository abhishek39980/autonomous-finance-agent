"""
Default tools for the agent.
"""

from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any, List, Optional

from .base_tool import BaseTool, ToolResponse


class SearchTool(BaseTool):
    """Simple web search tool (placeholder)."""

    @property
    def name(self) -> str:
        return "search"

    @property
    def description(self) -> str:
        return "Search the web for information. Input: query (str)."

    def run(self, query: str, **kwargs: Any) -> ToolResponse:
        if not query:
            return self._fail("query is required")
        # Placeholder implementation
        return self._ok({"results": f"Search results for '{query}' (placeholder)"})


class FileTool(BaseTool):
    """File reading and writing tool."""

    @property
    def name(self) -> str:
        return "file"

    @property
    def description(self) -> str:
        return "Read or write files. Input: action (read/write), path (str), content (str for write)."

    def run(self, action: str, path: str, content: Optional[str] = None, **kwargs: Any) -> ToolResponse:
        if action not in ["read", "write"]:
            return self._fail("action must be 'read' or 'write'")
        if not path:
            return self._fail("path is required")

        try:
            if action == "read":
                with open(path, "r", encoding="utf-8") as f:
                    data = f.read()
                return self._ok({"content": data})
            else:  # write
                if content is None:
                    return self._fail("content is required for write")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return self._ok({"message": f"Written to {path}"})
        except Exception as e:
            return self._fail(str(e))


class CalculatorTool(BaseTool):
    """Simple calculator tool."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Perform mathematical calculations. Input: expression (str)."

    def run(self, expression: str, **kwargs: Any) -> ToolResponse:
        if not expression:
            return self._fail("expression is required")

        try:
            # Safe evaluation with limited builtins
            allowed_names = {
                k: v for k, v in math.__dict__.items() if not k.startswith("__")
            }
            allowed_names.update({"__builtins__": {}})
            result = eval(expression, allowed_names)
            return self._ok({"result": result})
        except Exception as e:
            return self._fail(str(e))
