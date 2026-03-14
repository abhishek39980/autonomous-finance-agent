"""
LLM client — supports LM Studio (OpenAI-compatible API) and Ollama.
Reads model_id from config; no hardcoded model names.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests

from .config import LLMConfig


class LLMClient:
    """
    Unified LLM client.
    - LM Studio: OpenAI-compatible endpoint on port 1234
    - Ollama:    Native API on port 11434
    Both are auto-detected from config.base_url.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.model_id = config.model_id
        # Detect provider from base_url
        self.is_ollama = "11434" in self.base_url

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        """Send a prompt and return the text completion."""
        if self.is_ollama:
            return self._complete_ollama(prompt, system, max_tokens)
        return self._complete_lmstudio(prompt, system, max_tokens)

    # ── LM Studio (OpenAI-compatible) ─────────────────────────────────────────

    def _complete_lmstudio(self, prompt: str, system: Optional[str] = None,
                           max_tokens: Optional[int] = None) -> str:
        url = f"{self.base_url}/chat/completions"

        # Many GGUF models reject "system" role — merge into user message
        full_prompt = prompt
        if system:
            full_prompt = f"[INST] {system} [/INST]\n\n{prompt}"

        payload = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": False,
        }

        try:
            r = requests.post(url, json=payload, timeout=self.config.timeout_seconds)
            if r.status_code == 400:
                print(f"\n❌ LM Studio Error (400): {r.text}")
            r.raise_for_status()
            data = r.json()
            if "choices" in data and data["choices"]:
                return (data["choices"][0]["message"]["content"] or "").strip()
            return ""
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "❌ Cannot connect to LM Studio. "
                "Make sure it is running and 'Start Server' is enabled on port 1234."
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LM Studio request failed: {e}") from e

    # ── Ollama ─────────────────────────────────────────────────────────────────

    def _complete_ollama(self, prompt: str, system: Optional[str] = None,
                         max_tokens: Optional[int] = None) -> str:
        url = f"{self.base_url}/api/generate"
        full_prompt = f"{system}\n\n{prompt}" if system else prompt

        payload = {
            "model": self.model_id,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": max_tokens or self.config.max_tokens,
            },
        }

        try:
            r = requests.post(url, json=payload, timeout=self.config.timeout_seconds)
            r.raise_for_status()
            return (r.json().get("response") or "").strip()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "❌ Cannot connect to Ollama. "
                "Make sure Ollama is running (`ollama serve`) and model is pulled."
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama request failed: {e}") from e

    # ── JSON helper ───────────────────────────────────────────────────────────

    def complete_json(self, prompt: str, system: Optional[str] = None) -> dict[str, Any]:
        """Request JSON response and parse it."""
        json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No Markdown, no explanation."
        raw = self.complete(json_prompt, system=system).strip()

        if "```json" in raw:
            m = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
            if m:
                raw = m.group(1).strip()
        elif "```" in raw:
            m = re.search(r"```\s*([\s\S]*?)\s*```", raw)
            if m:
                raw = m.group(1).strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw, "error": "Failed to parse JSON"}