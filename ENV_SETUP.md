# Environment Setup Guide

## Quick Setup with .env File

### Step 1: Install python-dotenv

```bash
# Activate virtual environment
. .venv/bin/activate

# Install python-dotenv (now in dependencies)
pip install -e .[dev]
```

### Step 2: Create Your .env File

```bash
# Copy the example file
cp .env.example .env

# Edit with your favorite editor
nano .env  # or vim, code, etc.
```

### Step 3: Add Your API Keys

Edit `.env` file and add your actual keys:

```bash
# Required for LLM functionality
OPENAI_API_KEY=sk-proj-your-actual-openai-key-here

# Optional: For premium narratives with Claude
ANTHROPIC_API_KEY=sk-ant-your-actual-anthropic-key-here

# Optional: Configuration
LLM_DEBUG=false
LLM_COST_TRACKING=true
```

### Step 4: Verify It Works

```bash
# The .env file will be automatically loaded!
python scripts/test_llm.py

# Generate a report - no need to export!
python scripts/generate_full_report.py META --output-dir out
```

## How It Works

The system now automatically loads `.env` files in this order:
1. Checks for `.env` in the project root
2. Auto-loads when any script runs
3. Falls back to exported environment variables if no .env file

## Security Notes

⚠️ **IMPORTANT**: Never commit your `.env` file!
- The `.env` file is already in `.gitignore`
- Keep `.env.example` with dummy values for reference
- Each developer should create their own `.env` file

## Benefits

✅ **No more exporting**: Keys persist across terminal sessions
✅ **Easy switching**: Different keys for dev/prod in separate .env files  
✅ **Team friendly**: Each developer has their own .env file
✅ **Secure**: .env files are gitignored by default

## Troubleshooting

### .env File Not Loading?

```bash
# Check if file exists
ls -la .env

# Check if dotenv is installed
pip show python-dotenv

# Debug mode - see if it's loading
export LLM_DEBUG=true
python -c "from investing_agent.config import load_env_file; print(load_env_file())"
```

### Still Need to Export?

If .env isn't working, you can still export manually:
```bash
export OPENAI_API_KEY="sk-proj-..."
```

## Alternative: Using direnv (Advanced)

For automatic environment switching when entering the directory:

```bash
# Install direnv
brew install direnv  # macOS
# or: apt-get install direnv  # Ubuntu

# Add to shell
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc  # or ~/.zshrc

# Create .envrc file
echo 'source .env' > .envrc
direnv allow
```

Now environment loads automatically when you `cd` into the project!