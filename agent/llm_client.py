"""
LLM client for LM Studio.
Fixes 'Only user and assistant roles supported' error by merging system prompts.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

import requests

from .config import LLMConfig


class LLMClient:
    """LM Studio HTTP client."""

    def __init__(self, config: LLMConfig):
        self.config = config
        # Force correct port
        if "11434" in config.base_url:
            self.base_url = "http://localhost:1234/v1"
        else:
            self.base_url = config.base_url.rstrip("/")

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: Optional[int] = None) -> str:
        """Send prompt to LM Studio."""
        url = f"{self.base_url}/chat/completions"
        
        # FIX: Merge System Prompt into User Prompt
        # Many GGUF models in LM Studio crash if you send "role": "system".
        full_prompt = prompt
        if system:
            full_prompt = f"INSTRUCTION: {system}\n\nUSER QUERY: {prompt}"

        messages = [{"role": "user", "content": full_prompt}]

        payload = {
            "model": "mistral-7b-instruct-v0.2",
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            "stream": False
        }

        try:
            r = requests.post(url, json=payload, timeout=self.config.timeout_seconds)
            
            if r.status_code == 400:
                print(f"\n❌ LM Studio Error (400): {r.text}")
            
            r.raise_for_status()
            data = r.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                return (content or "").strip()
            else:
                return ""
            
        except requests.exceptions.RequestException as e:
            if "Connection refused" in str(e):
                raise RuntimeError("Connection failed. Check Port 1234 in LM Studio.")
            raise RuntimeError(f"LM Studio request failed: {e}") from e

    def complete_json(self, prompt: str, system: Optional[str] = None) -> dict[str, Any]:
        """Request JSON response."""
        json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No Markdown."
        
        raw = self.complete(json_prompt, system=system)
        raw = raw.strip()

        # Regex to extract JSON block
        if "```json" in raw:
            m = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
            if m: raw = m.group(1).strip()
        elif "```" in raw:
            m = re.search(r"```\s*([\s\S]*?)\s*```", raw)
            if m: raw = m.group(1).strip()
        
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw, "error": "Failed to parse JSON"}