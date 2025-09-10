#!/usr/bin/env python3
"""Quick test to verify API key is loaded."""

import os
import sys
from pathlib import Path

# Add parent to path and load config
sys.path.insert(0, str(Path(__file__).parent.parent))
from investing_agent.config import load_env_file

# Load environment
env_path = load_env_file()

# Check results
print("="*50)
print("API KEY STATUS CHECK")
print("="*50)
print()

if env_path:
    print(f"✅ Loaded .env from: {env_path}")
else:
    print("❌ No .env file found")
    
api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    if "REPLACE-WITH-YOUR-ACTUAL-KEY" in api_key:
        print("⚠️  OpenAI key found but still has placeholder text")
        print("    Please edit .env and add your actual key")
    elif api_key.startswith("sk-"):
        # Show first/last few chars for verification (keep most hidden)
        masked = f"{api_key[:7]}...{api_key[-4:]}"
        print(f"✅ OpenAI key loaded: {masked}")
        print()
        print("🎉 You're ready to generate reports with LLM!")
        print("   Run: python scripts/generate_full_report.py META --output-dir out")
    else:
        print("⚠️  OpenAI key found but doesn't look valid")
        print("    Keys should start with 'sk-'")
else:
    print("❌ OpenAI key not found")
    print("   Please add OPENAI_API_KEY to your .env file")