# Troubleshooting Guide for Full Report Generation

## Common Issues and Solutions

### 1. API Key Not Working

**Error**: `OPENAI_API_KEY not set` or `Invalid API key`

**Solution**:
```bash
# Check if key is set
echo $OPENAI_API_KEY

# Set the key (replace with your actual key)
export OPENAI_API_KEY="sk-proj-..."

# Verify it works
python scripts/test_llm.py
```

### 2. LLM Call Failures

**Error**: `LLMProvider.call is not implemented for live calls`

**Solution**: This means the API key is not set. See solution #1.

**Error**: `Rate limit exceeded` or `Insufficient quota`

**Solution**: 
- Check your OpenAI account credits
- Use cheaper models: Edit `investing_agent/agents/writer_llm_gen.py` and change "gpt-4" to "gpt-3.5-turbo"

### 3. Import Errors

**Error**: `ModuleNotFoundError: No module named 'openai'`

**Solution**:
```bash
# Ensure virtual environment is activated
. .venv/bin/activate

# Reinstall dependencies
pip install -e .[dev]
```

### 4. Evidence Pipeline Not Working

**Error**: `Evidence pipeline not available`

**Solution**: Evidence pipeline requires LLM. Ensure API key is set.

### 5. Low Quality Scores

If your report scores below 6.0/10:

1. **Check LLM is working**: Narrative sections should have content
2. **Enable all features**: Don't use `--no-evidence` or `--no-comparables` flags
3. **Review the report**: Check `out/META/META_professional_report.md` for missing sections

### 6. Memory/Performance Issues

For large reports:
```bash
# Use minimal features first
python scripts/generate_full_report.py META \
    --no-evidence \
    --no-comparables \
    --output-dir out

# Then gradually enable features
python scripts/generate_full_report.py META \
    --no-evidence \
    --output-dir out
```

## Quick Diagnostic Script

```bash
# Run this to check your setup
python -c "
import os
import sys

checks = {
    'Python Version': sys.version.split()[0],
    'OPENAI_API_KEY': 'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET',
    'Virtual Env': 'ACTIVE' if 'venv' in sys.prefix else 'NOT ACTIVE',
}

print('System Check:')
for check, status in checks.items():
    emoji = '✅' if status not in ['NOT SET', 'NOT ACTIVE'] else '❌'
    print(f'  {emoji} {check}: {status}')
"
```

## Getting Help

If issues persist:
1. Check the generation log: `cat out/META/generation.log`
2. Review error messages carefully
3. Ensure all dependencies are installed: `pip list | grep -E 'openai|anthropic|numpy|pydantic'`