#!/usr/bin/env python3
"""Test LLM connectivity."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from investing_agent.llm.provider import LLMProvider

def test_llm():
    """Test LLM connectivity."""
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set")
        print("Please run: export OPENAI_API_KEY='your-api-key'")
        return False
    
    print("✅ OPENAI_API_KEY is set")
    
    # Test LLM call
    try:
        provider = LLMProvider()
        response = provider.call(
            "gpt-3.5-turbo",  # Use cheaper model for test
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'LLM is working' in 5 words or less"}
            ],
            params={"temperature": 0, "max_tokens": 20}
        )
        print(f"✅ LLM Response: {response}")
        return True
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        return False

if __name__ == "__main__":
    success = test_llm()
    sys.exit(0 if success else 1)