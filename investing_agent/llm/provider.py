from __future__ import annotations

"""
Deterministic LLM provider shim (no live calls in CI).

Usage:
- LLMProvider.call(model_id, messages, params) -> dict response
- This module does not implement any real network calls; in CI, live use should be disabled.
"""

from typing import Any, Dict, List
import os


class LLMProvider:
    def call(self, model_id: str, messages: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        if os.environ.get("CI", "").lower() in {"1", "true", "yes"}:
            raise RuntimeError("Live LLM calls are disabled in CI")
        # Placeholder: no real HTTP call implemented
        raise NotImplementedError("LLMProvider.call is not implemented for live calls in this project")

