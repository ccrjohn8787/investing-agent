"""Configuration module with .env file support."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Find the .env file by walking up from current file
def load_env_file():
    """Load .env file from project root if it exists."""
    current_dir = Path(__file__).parent
    
    # Try to find .env file in parent directories
    for parent in [current_dir.parent.parent, current_dir.parent, current_dir]:
        env_file = parent / '.env'
        if env_file.exists():
            load_dotenv(env_file)
            return str(env_file)
    
    # Also check working directory
    if Path('.env').exists():
        load_dotenv('.env')
        return '.env'
    
    return None

# Automatically load .env when module is imported
env_path = load_env_file()

if env_path and os.getenv('LLM_DEBUG') == 'true':
    print(f"✅ Loaded environment from: {env_path}")

# Export configuration
def get_api_key(provider: str) -> str:
    """Get API key for a provider from environment."""
    key_map = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'together': 'TOGETHER_API_KEY',
    }
    
    env_var = key_map.get(provider.lower())
    if not env_var:
        return None
    
    return os.getenv(env_var)