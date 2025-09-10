from __future__ import annotations

"""
Deterministic LLM provider shim (no live calls in CI).

Usage:
- LLMProvider.call(model_id, messages, params) -> dict response
- This module does not implement any real network calls; in CI, live use should be disabled.
"""

from typing import Any, Dict, List
import os

# Auto-load .env file if present
try:
    from investing_agent.config import load_env_file
    load_env_file()
except ImportError:
    pass


class LLMProvider:
    def call(self, model_id: str, messages: List[Dict[str, Any]], params: Dict[str, Any]) -> str:
        """Make actual OpenAI API calls."""
        if os.environ.get("CI", "").lower() in {"1", "true", "yes"}:
            raise RuntimeError("Live LLM calls are disabled in CI")
        
        # Get API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        
        try:
            from openai import OpenAI
            
            # Initialize client
            client = OpenAI(api_key=api_key)
            
            # Make the API call
            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=params.get("temperature", 0.3),
                max_tokens=params.get("max_tokens", 500),
                top_p=params.get("top_p", 1.0),
                frequency_penalty=params.get("frequency_penalty", 0),
                presence_penalty=params.get("presence_penalty", 0),
            )
            
            # Return the content
            return response.choices[0].message.content
            
        except Exception as e:
            # Log error and return fallback
            print(f"LLM call failed: {e}")
            raise

