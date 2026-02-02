"""
Agent configuration loader. Model swap via config only—no code changes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class LLMConfig:
    provider: str
    model_id: str
    base_url: str
    timeout_seconds: int
    max_tokens: int
    temperature: float


@dataclass
class EmbeddingsConfig:
    model_id: str
    dimension: int


@dataclass
class MemoryConfig:
    vector_store_path: str
    top_k: int
    similarity_threshold: float
    recency_weight: float


@dataclass
class EvaluationConfig:
    confidence_threshold: float
    max_retries_per_step: int


@dataclass
class ToolsConfig:
    code_execution_timeout_seconds: int
    web_request_timeout_seconds: int
    web_request_delay_seconds: float
    max_web_results: int


@dataclass
class LoggingConfig:
    dir: str
    level: str
    format: str


@dataclass
class SafetyConfig:
    refuse_harmful: bool
    max_file_size_bytes: int
    allowed_file_extensions: list[str]


@dataclass
class AgentConfig:
    """Top-level agent configuration. Load from config.yaml."""

    llm: LLMConfig
    embeddings: EmbeddingsConfig
    memory: MemoryConfig
    evaluation: EvaluationConfig
    tools: ToolsConfig
    logging: LoggingConfig
    safety: SafetyConfig

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AgentConfig:
        def _llm(c: dict) -> LLMConfig:
            return LLMConfig(
                provider=c.get("provider", "ollama"),
                model_id=c.get("model_id", "mistral"),
                base_url=c.get("base_url", "http://localhost:11434"),
                timeout_seconds=c.get("timeout_seconds", 120),
                max_tokens=c.get("max_tokens", 2048),
                temperature=c.get("temperature", 0.3),
            )

        def _embeddings(c: dict) -> EmbeddingsConfig:
            return EmbeddingsConfig(
                model_id=c.get("model_id", "sentence-transformers/all-MiniLM-L6-v2"),
                dimension=c.get("dimension", 384),
            )

        def _memory(c: dict) -> MemoryConfig:
            return MemoryConfig(
                vector_store_path=c.get("vector_store_path", "data/faiss_index"),
                top_k=c.get("top_k", 5),
                similarity_threshold=c.get("similarity_threshold", 0.7),
                recency_weight=c.get("recency_weight", 0.3),
            )

        def _evaluation(c: dict) -> EvaluationConfig:
            return EvaluationConfig(
                confidence_threshold=c.get("confidence_threshold", 0.6),
                max_retries_per_step=c.get("max_retries_per_step", 3),
            )

        def _tools(c: dict) -> ToolsConfig:
            return ToolsConfig(
                code_execution_timeout_seconds=c.get("code_execution_timeout_seconds", 10),
                web_request_timeout_seconds=c.get("web_request_timeout_seconds", 15),
                web_request_delay_seconds=c.get("web_request_delay_seconds", 1.0),
                max_web_results=c.get("max_web_results", 5),
            )

        def _logging(c: dict) -> LoggingConfig:
            return LoggingConfig(
                dir=c.get("dir", "logs"),
                level=c.get("level", "INFO"),
                format=c.get("format", "jsonl"),
            )

        def _safety(c: dict) -> SafetyConfig:
            return SafetyConfig(
                refuse_harmful=c.get("refuse_harmful", True),
                max_file_size_bytes=c.get("max_file_size_bytes", 10 * 1024 * 1024),
                allowed_file_extensions=c.get("allowed_file_extensions", [".txt", ".md", ".json"]),
            )

        return cls(
            llm=_llm(d.get("llm", {})),
            embeddings=_embeddings(d.get("embeddings", {})),
            memory=_memory(d.get("memory", {})),
            evaluation=_evaluation(d.get("evaluation", {})),
            tools=_tools(d.get("tools", {})),
            logging=_logging(d.get("logging", {})),
            safety=_safety(d.get("safety", {})),
        )


def load_config(path: str | Path | None = None) -> AgentConfig:
    """Load config from YAML file. Default: config.yaml in project root."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "config.yaml"
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return AgentConfig.from_dict(data)
