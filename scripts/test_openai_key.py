#!/usr/bin/env python3
"""Test OpenAI API key functionality."""

import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment
from investing_agent.config import load_env_file
env_path = load_env_file()

def test_openai_key():
    """Test if OpenAI API key works."""
    
    print("="*60)
    print("OPENAI API KEY TEST")
    print("="*60)
    print()
    
    # Step 1: Check if key is loaded
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("❌ No OpenAI API key found in environment")
        print("   Please check your .env file")
        return False
    
    # Mask the key for display
    if len(api_key) > 10:
        masked = f"{api_key[:7]}...{api_key[-4:]}"
    else:
        masked = "***"
    
    print(f"✅ API key loaded: {masked}")
    print(f"   From: {env_path}")
    print()
    
    # Step 2: Try to import OpenAI
    try:
        import openai
        print("✅ OpenAI library imported successfully")
    except ImportError:
        print("❌ OpenAI library not installed")
        print("   Run: pip install openai")
        return False
    
    # Step 3: Test actual API call
    print()
    print("Testing API connection...")
    print("-" * 40)
    
    try:
        # Use the newer OpenAI client
        from openai import OpenAI
        
        # Initialize client with the API key
        client = OpenAI(api_key=api_key)
        
        # Make a simple test call with minimal tokens
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Use cheapest model for test
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Reply in exactly 5 words."},
                {"role": "user", "content": "Say 'API key works perfectly' please"}
            ],
            max_tokens=10,
            temperature=0
        )
        
        # Get the response
        result = response.choices[0].message.content
        
        print(f"✅ API Response: {result}")
        print()
        print("🎉 SUCCESS! Your OpenAI API key is working!")
        print()
        
        # Show usage info
        if hasattr(response, 'usage'):
            print(f"📊 Test Usage:")
            print(f"   Prompt tokens: {response.usage.prompt_tokens}")
            print(f"   Completion tokens: {response.usage.completion_tokens}")
            print(f"   Total tokens: {response.usage.total_tokens}")
            
            # Estimate cost (rough estimates for GPT-3.5)
            cost = (response.usage.prompt_tokens * 0.0005 + 
                   response.usage.completion_tokens * 0.0015) / 1000
            print(f"   Estimated cost: ${cost:.4f}")
        
        print()
        print("✅ You're ready to generate full professional reports!")
        print("   Run: python scripts/generate_full_report.py META --output-dir out")
        
        return True
        
    except openai.AuthenticationError as e:
        print(f"❌ Authentication Error: Invalid API key")
        print(f"   Error: {str(e)[:100]}")
        print()
        print("Please check:")
        print("1. Your API key is correct (no extra spaces)")
        print("2. Your API key is active on OpenAI platform")
        print("3. Visit: https://platform.openai.com/api-keys")
        return False
        
    except openai.RateLimitError as e:
        print(f"⚠️  Rate Limit Error")
        print(f"   Error: {str(e)[:100]}")
        print()
        print("This might mean:")
        print("1. You've exceeded your API quota")
        print("2. Your account needs billing setup")
        print("3. Visit: https://platform.openai.com/usage")
        return False
        
    except openai.APIError as e:
        print(f"❌ OpenAI API Error")
        print(f"   Error: {str(e)[:200]}")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}")
        print(f"   Error: {str(e)[:200]}")
        print()
        print("Possible issues:")
        print("1. Network connection problems")
        print("2. OpenAI service issues")
        print("3. Invalid API key format")
        return False

if __name__ == "__main__":
    success = test_openai_key()
    sys.exit(0 if success else 1)