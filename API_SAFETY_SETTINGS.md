# API Safety Settings & Cost Management

## 🔒 Current Configuration

### Default Model: GPT-4o-mini
- **Cost**: $0.0008 per report
- **Quality**: 95% of GPT-4 quality
- **Speed**: 2-3x faster than GPT-4
- **Usage**: Automatically used unless explicitly overridden

### Model Options
| Mode | Model | Cost/Report | When to Use |
|------|-------|-------------|-------------|
| `standard` (DEFAULT) | GPT-4o-mini | $0.0008 | Daily reports, regular analysis |
| `premium` | GPT-4 | $0.15 | Only when explicitly requested |
| `budget` | GPT-3.5-turbo | $0.003 | Quick drafts, bulk generation |

## ⚠️ Safety Rules

### 1. **Never Run Without Permission**
- Always ask before calling OpenAI API
- Show estimated cost before proceeding
- Require explicit confirmation for batches > 3

### 2. **Default to Cheaper Models**
- Use GPT-4o-mini by default
- Only use GPT-4 when user explicitly says "premium" or "use GPT-4"
- Warn if cost will exceed $1.00

### 3. **Cost Tracking**
- Show cost estimates before running
- Track actual costs when LLM_COST_TRACKING=true
- Alert on high-cost operations

## 📊 Usage Examples

### Safe Usage (Default GPT-4o-mini)
```bash
# Single report - uses GPT-4o-mini by default
python scripts/generate_full_report.py AAPL --output-dir out

# Cost: $0.0008
```

### Premium Usage (GPT-4 - Only When Requested)
```bash
# User must explicitly request premium
python scripts/generate_full_report.py AAPL --llm-quality premium

# Cost: $0.15 (187x more expensive!)
```

### Batch Generation with Safety
```bash
# Use safe generator for multiple reports
python scripts/safe_report_generator.py AAPL MSFT GOOGL

# Will prompt:
# 📊 Reports to Generate: 3
# 💵 Estimated Cost: $0.0024
# Do you want to proceed? (y/n):
```

## 💰 Budget Management

### With $10 Monthly Budget

| Model | Reports per $10 | Use Case |
|-------|-----------------|----------|
| GPT-4o-mini | 12,500 reports | Default for everything |
| GPT-3.5-turbo | 3,333 reports | Bulk/draft generation |
| GPT-4 | 66 reports | Premium only when needed |

### Recommended Strategy
1. **Use GPT-4o-mini (standard) for 99% of reports**
2. **Reserve GPT-4 (premium) for client presentations only**
3. **Use GPT-3.5 (budget) for bulk testing**

## 🛡️ Safety Scripts

### Safe Report Generator
```bash
# Automatically confirms costs and limits
python scripts/safe_report_generator.py TICKER

# Skip confirmation (use carefully)
python scripts/safe_report_generator.py TICKER --force
```

### Test Without API Calls
```bash
# Use demo mode (no API calls)
make demo

# Generate with template only
python scripts/generate_full_report.py TICKER --no-llm
```

## 📝 CLAUDE.md Integration

The following rules are now in CLAUDE.md:
- Never run API calls without asking
- Default to GPT-4o-mini
- Show costs before running
- Limit batch sizes
- Only use GPT-4 when explicitly requested

## ✅ Verification

Current settings ensure:
- **No accidental high costs**: GPT-4o-mini by default
- **No surprise charges**: Always show cost estimates
- **No runaway generation**: Batch limits enforced
- **Full cost transparency**: Tracking enabled

Your API usage is now protected with:
- 200x cost reduction by default
- Explicit confirmation requirements
- Clear cost visibility
- Safe batch limits