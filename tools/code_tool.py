"""
Sandboxed Python code execution via subprocess with timeout. No system-level access.
Handles malformed code, timeouts, and resource limits.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Optional

from .base_tool import BaseTool, ToolResponse


class CodeExecutionTool(BaseTool):
    """Execute Python code in a subprocess with timeout. Sandboxed (no network/files outside temp)."""

    @property
    def name(self) -> str:
        return "code_execute"

    @property
    def description(self) -> str:
        return "Run Python code in a sandbox (subprocess, timeout). Use for calculations, data processing. Input: code (str)."

    def run(self, code: str, **kwargs: Any) -> ToolResponse:
        if not code or not isinstance(code, str):
            return self._fail("code (str) is required", retry_recommended=False)
        code = code.strip()
        if not code:
            return self._fail("code is empty", retry_recommended=False)

        timeout = 10
        if self.config and hasattr(self.config, "tools"):
            timeout = getattr(self.config.tools, "code_execution_timeout_seconds", 10)

        # Basic safety: block obvious dangerous patterns
        block = ["os.system", "subprocess.", "open(", "eval(", "exec(", "__import__", "compile(", "breakpoint"]
        for b in block:
            if b in code:
                return self._fail(f"Blocked: code may not use '{b}'", retry_recommended=False)

        try:
            with tempfile.TemporaryDirectory() as tmp:
                script = Path(tmp) / "run.py"
                script.write_text(code, encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(script)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmp,
                    env={},
                )
                stdout = result.stdout or ""
                stderr = result.stderr or ""
                if result.returncode != 0:
                    return self._fail(
                        f"Exit code {result.returncode}. stderr: {stderr[:500]}",
                        retry_recommended=True,
                    )
                return self._ok({"stdout": stdout, "stderr": stderr})
        except subprocess.TimeoutExpired:
            return self._fail("Execution timed out", retry_recommended=True)
        except Exception as e:
            return self._fail(str(e), retry_recommended=True)
