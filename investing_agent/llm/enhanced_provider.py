from __future__ import annotations

"""
Enhanced LLM Provider with multi-model support and authentication.

Features:
- Support for OpenAI, Anthropic, and other providers
- Environment-based authentication  
- Model routing and fallback strategies
- Rate limiting and retry logic
- Cost tracking and usage monitoring
- Deterministic settings for reproducibility
"""

import os
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    TOGETHER = "together"
    LOCAL = "local"


@dataclass
class ModelConfig:
    provider: ModelProvider
    model_id: str
    max_tokens: int = 4000
    temperature: float = 0.0
    top_p: float = 1.0
    seed: Optional[int] = 2025
    cost_per_1k_input: float = 0.01  # USD
    cost_per_1k_output: float = 0.03  # USD
    max_context: int = 128000


class LLMProvider:
    """Enhanced LLM provider with multi-model support and best practices."""
    
    # Model registry with current production models and pricing
    MODELS = {
        # Story & Narrative Generation (High Quality)
        "story-premium": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-3-5-sonnet-20241022",  # Current Claude 3.5 Sonnet
            max_tokens=4000,
            temperature=0.3,  # Slightly creative for narrative
            cost_per_1k_input=0.003,  # $3 per million
            cost_per_1k_output=0.015,  # $15 per million
            max_context=200000  # 200K context window
        ),
        "story-premium-plus": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-3-opus-20240229",  # Claude 3 Opus for ultimate quality
            max_tokens=4000,
            temperature=0.3,
            cost_per_1k_input=0.015,  # $15 per million
            cost_per_1k_output=0.075,  # $75 per million
            max_context=200000
        ),
        "story-standard": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4o",  # Current GPT-4o
            max_tokens=4000,
            temperature=0.3,
            cost_per_1k_input=0.005,  # $5 per million
            cost_per_1k_output=0.015,  # $15 per million
            max_context=128000  # 128K context
        ),
        
        # Research & Analysis (High Reasoning)
        "research-premium": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4o",  # Current GPT-4o for research
            max_tokens=4000,
            temperature=0.0,  # Deterministic for analysis
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
            max_context=128000
        ),
        "research-ultimate": ModelConfig(
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-3-opus-20240229",  # For complex analysis requiring deep reasoning
            max_tokens=4000,
            temperature=0.0,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
            max_context=200000
        ),
        "research-standard": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4-turbo",  # GPT-4 Turbo for standard research
            max_tokens=4000,
            temperature=0.0,
            cost_per_1k_input=0.010,
            cost_per_1k_output=0.030,
            max_context=128000
        ),
        
        # Evaluation & Judging (Consistency)
        "judge-primary": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4-turbo",  # GPT-4 Turbo for consistent evaluation
            max_tokens=4000,
            temperature=0.0,  # Fully deterministic
            top_p=1.0,
            seed=2025,
            cost_per_1k_input=0.010,
            cost_per_1k_output=0.030,
            max_context=128000
        ),
        "judge-enhanced": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4o",  # GPT-4o for enhanced evaluation
            max_tokens=4000,
            temperature=0.0,
            top_p=1.0,
            seed=2025,
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
            max_context=128000
        ),
        
        # Quick Tasks (Cost Effective)
        "quick-task": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4o-mini",  # GPT-4o Mini for cost-effective tasks
            max_tokens=2000,
            temperature=0.0,
            cost_per_1k_input=0.00015,  # $0.15 per million
            cost_per_1k_output=0.0006,  # $0.60 per million
            max_context=128000
        ),
        
        # Development/Testing (Cost effective)
        "dev-test": ModelConfig(
            provider=ModelProvider.OPENAI,
            model_id="gpt-4o-mini",  # GPT-4o Mini for development
            max_tokens=2000,
            temperature=0.0,
            cost_per_1k_input=0.00015,
            cost_per_1k_output=0.0006,
            max_context=128000
        )
    }
    
    def __init__(self, enable_caching: bool = True, cache_dir: str = ".cache/llm"):
        """Initialize provider with authentication and settings."""
        self.usage_tracking = {}
        self.enable_caching = enable_caching
        self.cache_dir = Path(cache_dir)
        
        if enable_caching:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._validate_authentication()
    
    def _validate_authentication(self):
        """Validate that necessary API keys are available and secure."""
        auth_status = {}
        security_warnings = []
        
        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            if self._is_secure_key(openai_key, "sk-"):
                auth_status["openai"] = "✓ Available"
            else:
                auth_status["openai"] = "⚠ Available (insecure format)"
                security_warnings.append("OpenAI API key format appears invalid")
        else:
            auth_status["openai"] = "✗ Missing OPENAI_API_KEY"
        
        # Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            if self._is_secure_key(anthropic_key, "sk-ant-"):
                auth_status["anthropic"] = "✓ Available"
            else:
                auth_status["anthropic"] = "⚠ Available (insecure format)"
                security_warnings.append("Anthropic API key format appears invalid")
        else:
            auth_status["anthropic"] = "✗ Missing ANTHROPIC_API_KEY"
        
        # Together AI (optional)
        together_key = os.getenv("TOGETHER_API_KEY")
        if together_key:
            auth_status["together"] = "✓ Available"
        else:
            auth_status["together"] = "✗ Missing TOGETHER_API_KEY (optional)"
        
        # Security checks
        if os.path.exists(".env") and not os.path.exists(".gitignore"):
            security_warnings.append(".env file exists but no .gitignore found")
        
        # Check for hardcoded keys in code (basic check)
        if any(key and len(key) > 20 and key.startswith(("sk-", "sk-ant-")) for key in [openai_key, anthropic_key]):
            if os.getenv("CI") != "true":  # Skip warning in CI
                import sys
                if any("OPENAI_API_KEY" in line or "ANTHROPIC_API_KEY" in line for line in sys.argv):
                    security_warnings.append("API key passed via command line (insecure)")
        
        self.auth_status = auth_status
        self.security_warnings = security_warnings
        
        # Print security warnings if any
        if security_warnings and os.getenv("LLM_DEBUG", "").lower() in ("true", "1"):
            print("🔐 Security Warnings:")
            for warning in security_warnings:
                print(f"  ⚠ {warning}")
    
    def _is_secure_key(self, key: str, expected_prefix: str) -> bool:
        """Basic validation of API key format."""
        if not key or not isinstance(key, str):
            return False
        
        # Check prefix and minimum length
        if not key.startswith(expected_prefix):
            return False
            
        # Basic length checks (OpenAI ~51 chars, Anthropic ~108 chars)
        if expected_prefix == "sk-" and len(key) < 40:
            return False
        elif expected_prefix == "sk-ant-" and len(key) < 80:
            return False
            
        return True
    
    def call(
        self, 
        model_name: str, 
        messages: List[Dict[str, Any]], 
        params: Optional[Dict[str, Any]] = None,
        fallback_model: Optional[str] = None,
        cassette_path: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Call LLM with enhanced features.
        
        Args:
            model_name: Model name from MODELS registry
            messages: OpenAI-format messages
            params: Optional parameter overrides
            fallback_model: Fallback model if primary fails
            cassette_path: Path to cassette for deterministic testing
            
        Returns:
            LLM response in standardized format
        """
        # CI mode - disable live calls
        if os.environ.get("CI", "").lower() in {"1", "true", "yes"}:
            if cassette_path:
                return self._load_cassette(cassette_path)
            raise RuntimeError("Live LLM calls disabled in CI. Provide cassette_path for deterministic testing.")
        
        # Load from cassette if provided (for reproducible development)
        if cassette_path and os.path.exists(cassette_path):
            return self._load_cassette(cassette_path)
        
        # Check cache first (if enabled and deterministic)
        if use_cache and self.enable_caching:
            cache_key = self._generate_cache_key(model_name, messages, params)
            cached_response = self._load_from_cache(cache_key)
            if cached_response:
                return cached_response
        
        # Get model configuration
        if model_name not in self.MODELS:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(self.MODELS.keys())}")
        
        config = self.MODELS[model_name]
        
        # Apply parameter overrides
        effective_params = self._build_params(config, params)
        
        try:
            # Make actual LLM call based on provider
            if config.provider == ModelProvider.OPENAI:
                response = self._call_openai(config.model_id, messages, effective_params)
            elif config.provider == ModelProvider.ANTHROPIC:
                response = self._call_anthropic(config.model_id, messages, effective_params)
            else:
                raise NotImplementedError(f"Provider {config.provider} not yet implemented")
            
            # Track usage and costs
            self._track_usage(model_name, response, config)
            
            # Save to cache if enabled and deterministic
            if use_cache and self.enable_caching and effective_params.get("temperature", 1.0) == 0.0:
                cache_key = self._generate_cache_key(model_name, messages, params)
                self._save_to_cache(cache_key, response)
            
            return response
            
        except Exception as e:
            if fallback_model and fallback_model != model_name:
                print(f"Warning: {model_name} failed, trying fallback {fallback_model}")
                return self.call(fallback_model, messages, params, None, cassette_path)
            raise e
    
    def _call_openai(self, model_id: str, messages: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        """Make OpenAI API call."""
        try:
            import openai
        except ImportError:
            raise ImportError("OpenAI library not installed. Run: pip install openai")
        
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable required")
        
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            **params
        )
        
        # Convert to standardized format
        return {
            "choices": [
                {
                    "message": {
                        "content": response.choices[0].message.content,
                        "role": response.choices[0].message.role
                    }
                }
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "model": response.model
        }
    
    def _call_anthropic(self, model_id: str, messages: List[Dict[str, Any]], params: Dict[str, Any]) -> Dict[str, Any]:
        """Make Anthropic API call."""
        try:
            import anthropic
        except ImportError:
            raise ImportError("Anthropic library not installed. Run: pip install anthropic")
        
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY environment variable required")
        
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Convert OpenAI format to Anthropic format
        system_message = None
        conversation = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                conversation.append(msg)
        
        anthropic_params = {
            "model": model_id,
            "messages": conversation,
            "max_tokens": params.get("max_tokens", 4000)
        }
        
        if system_message:
            anthropic_params["system"] = system_message
        if "temperature" in params:
            anthropic_params["temperature"] = params["temperature"]
        if "top_p" in params:
            anthropic_params["top_p"] = params["top_p"]
        
        response = client.messages.create(**anthropic_params)
        
        # Convert to standardized format
        return {
            "choices": [
                {
                    "message": {
                        "content": response.content[0].text,
                        "role": "assistant"
                    }
                }
            ],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            },
            "model": response.model
        }
    
    def _build_params(self, config: ModelConfig, param_overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build effective parameters from config and overrides."""
        params = {
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "top_p": config.top_p
        }
        
        if config.seed is not None:
            params["seed"] = config.seed
        
        if param_overrides:
            params.update(param_overrides)
        
        return params
    
    def _track_usage(self, model_name: str, response: Dict[str, Any], config: ModelConfig):
        """Track usage and estimated costs."""
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        cost = (
            (prompt_tokens / 1000) * config.cost_per_1k_input +
            (completion_tokens / 1000) * config.cost_per_1k_output
        )
        
        if model_name not in self.usage_tracking:
            self.usage_tracking[model_name] = {
                "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_cost": 0.0
            }
        
        self.usage_tracking[model_name]["calls"] += 1
        self.usage_tracking[model_name]["prompt_tokens"] += prompt_tokens
        self.usage_tracking[model_name]["completion_tokens"] += completion_tokens
        self.usage_tracking[model_name]["total_cost"] += cost
    
    def _load_cassette(self, cassette_path: str) -> Dict[str, Any]:
        """Load response from cassette file."""
        try:
            with open(cassette_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load cassette {cassette_path}: {str(e)}")
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get detailed usage and cost report."""
        total_cost = sum(data["total_cost"] for data in self.usage_tracking.values())
        total_calls = sum(data["calls"] for data in self.usage_tracking.values())
        
        return {
            "total_calls": total_calls,
            "total_cost": total_cost,
            "by_model": self.usage_tracking,
            "auth_status": self.auth_status,
            "security_warnings": getattr(self, 'security_warnings', [])
        }
    
    @classmethod
    def get_recommended_model(cls, use_case: str) -> str:
        """Get recommended model for specific use case."""
        recommendations = {
            "story": "story-premium",
            "narrative": "story-premium", 
            "research": "research-premium",
            "analysis": "research-standard",
            "judge": "judge-primary",
            "evaluation": "judge-primary",
            "summary": "quick-task",
            "development": "dev-test"
        }
        
        return recommendations.get(use_case.lower(), "research-standard")
    
    def _generate_cache_key(self, model_name: str, messages: List[Dict[str, Any]], params: Optional[Dict[str, Any]]) -> str:
        """Generate deterministic cache key for request."""
        cache_data = {
            "model": model_name,
            "messages": messages,
            "params": params or {}
        }
        
        # Create hash of the request data
        cache_str = json.dumps(cache_data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(cache_str.encode()).hexdigest()[:16]
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load response from cache if available."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                
                # Check cache expiry (24 hours for deterministic calls)
                if cached_data.get("timestamp", 0) > time.time() - 86400:
                    return cached_data.get("response")
                    
            except Exception:
                # If cache is corrupted, ignore and proceed with fresh call
                pass
        
        return None
    
    def _save_to_cache(self, cache_key: str, response: Dict[str, Any]) -> None:
        """Save response to cache."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            cache_data = {
                "timestamp": time.time(),
                "response": response
            }
            
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
        except Exception:
            # Cache save failure should not break the flow
            pass


# Global provider instance
_provider = None

def get_provider() -> LLMProvider:
    """Get global LLM provider instance."""
    global _provider
    if _provider is None:
        _provider = LLMProvider()
    return _provider


# Convenience functions for common use cases
def call_story_model(messages: List[Dict[str, Any]], **params) -> Dict[str, Any]:
    """Call story/narrative generation model."""
    return get_provider().call("story-premium", messages, params)

def call_research_model(messages: List[Dict[str, Any]], **params) -> Dict[str, Any]:
    """Call research/analysis model."""
    return get_provider().call("research-premium", messages, params)

def call_judge_model(messages: List[Dict[str, Any]], **params) -> Dict[str, Any]:
    """Call evaluation/judging model."""
    return get_provider().call("judge-primary", messages, params)