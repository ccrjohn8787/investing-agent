#!/usr/bin/env python3
"""Minimal test to check API quota status."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from investing_agent.config import load_env_file

load_env_file()

def test_minimal():
    """Test with minimal token usage."""
    print("Testing OpenAI API with minimal usage...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Ultra-minimal test - just 1 token
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=1,
            temperature=0
        )
        
        print("✅ API is working!")
        print(f"Response: {response.choices[0].message.content}")
        
        # Try to check account info
        print("\nChecking account status...")
        models = client.models.list()
        print(f"✅ Can access {len(list(models.data))} models")
        
        return True
        
    except Exception as e:
        if "quota" in str(e).lower():
            print("❌ Quota exceeded - need to add billing")
            print("\nTo fix:")
            print("1. Go to: https://platform.openai.com/settings/organization/billing")
            print("2. Add a payment method")
            print("3. Set a monthly limit (e.g., $10)")
            print("4. Wait 2-5 minutes and try again")
        else:
            print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_minimal()