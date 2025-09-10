# Investing Agent

## Overview
Professional investment research platform generating institutional-grade equity reports with:
- **Minimalist HTML reports** (default) - Clean, readable, data-rich reports without JavaScript complexity
- **Deterministic DCF valuation** using four key drivers: sales growth, operating margin, WACC, and sales-to-capital
- **GPT-5 powered narratives** - Premium model (gpt-5) and standard model (gpt-5-mini) for professional analysis
- **Evidence-based research** with frozen snapshots and complete audit trails
- **Multi-dimensional evaluation** framework ensuring report quality (BYD benchmark standard)
- **Complete financial projections** - 10-year detailed tables with all metrics displayed

## Core Features
- **Minimalist Report Builder**: Clean HTML reports optimized for readability and print
- **Valuation Engine ("Ginzu")**: Pure NumPy DCF implementation with full reproducibility
- **Evidence Pipeline**: Research-once-then-freeze architecture with Model-PR logging
- **Professional Writer**: Story-to-numbers narrative generation matching analyst-grade quality
- **Quality Evaluation**: 5-dimensional scoring system with LLM-as-judge capabilities
- **Sensitivity Analysis**: Comprehensive valuation matrices across growth/margin scenarios

## Quick Start

### Setup
```bash
# Create virtual environment and install
python -m venv .venv && . .venv/bin/activate
pip install -e .[dev]

# Configure API keys (required for LLM features)
cp .env.example .env
# Edit .env to add your OPENAI_API_KEY
```

### Generate Reports (New Default: Minimalist HTML)
```bash
# Basic report with standard model (gpt-5-mini)
python scripts/report.py AAPL

# Premium report with gpt-5 for enhanced narratives
python scripts/report.py AAPL --premium

# Report with quality evaluation
python scripts/report.py AAPL --evaluate

# Report without LLM narratives (data only)
python scripts/report.py AAPL --disable-llm

# Legacy interactive report (if needed)
python scripts/report.py AAPL --interactive

# Demo report (no API calls)
make demo
```

## Report Types

### Minimalist HTML Reports (Default)
- **Clean, professional design** - No JavaScript, pure HTML/CSS
- **Complete data transparency** - All projections and calculations visible
- **Print-friendly** - Optimized for PDF export and printing
- **Reliability** - No interactive components to break
- **Full narratives** - Executive summary, financial analysis, investment thesis, risks, and conclusions

### Key Report Sections
- **Key Investment Metrics** - Current price, fair value, upside/downside, recommendation
- **DCF Valuation Summary** - Revenue, growth, margins, WACC, enterprise value
- **10-Year Financial Projections** - Detailed year-by-year breakdown
- **Sensitivity Analysis** - Valuation grid across different scenarios
- **Professional Narratives** - LLM-generated investment analysis
- **Evidence & Citations** - Source references with confidence levels
- **Quality Assessment** - Multi-dimensional scoring when evaluation enabled

## Model Configuration

### Standard Mode (Default)
- Model: **gpt-5-mini** (currently maps to gpt-4o-mini)
- Cost: ~$0.0008 per report
- Use for: Regular analysis and reporting

### Premium Mode
- Model: **gpt-5** (currently maps to gpt-4)
- Cost: ~$0.15 per report
- Use for: High-priority analysis requiring best quality
- Enable with: `--premium` flag

## Documentation
- **Setup & Configuration**: See `ENV_SETUP.md` and `API_SAFETY_SETTINGS.md`
- **Architecture**: See `AGENTS.md` for agent design and `docs/VALUATION_MATH.md` for DCF math
- **Evidence Pipeline**: See `EVIDENCE_PIPELINE_GUIDE.md` for research architecture
- **LLM Integration**: See `LLM_INTEGRATION_GUIDE.md` for model configuration
- **Report Evaluation**: See `REPORT_QUALITY_EVALUATION_README.md` for quality framework
- **UI Architecture**: See `docs/UI_ARCHITECTURE.md` for report generation system
- **Troubleshooting**: See `TROUBLESHOOTING.md` for common issues

## Current Status
- ✅ **P0**: LLM-Based Report Evaluation Framework
- ✅ **P1**: Evidence Pipeline with Research-Once Architecture
- ✅ **P2**: Professional Writer with Evidence Integration
- ✅ **P3**: Comparables & WACC Foundation
- ✅ **P4-6**: Professional Report Generation System
- ✅ **P7**: Evaluation Dashboard & Continuous Improvement
- ✅ **P8**: Minimalist HTML Reports (Default)
- ✅ **Safety**: API cost controls with gpt-5-mini default

## Project Structure
- `investing_agent/schemas`: Typed objects for inputs, outputs, and fundamentals
- `investing_agent/kernels`: Valuation kernel (Ginzu) pure NumPy implementation
- `investing_agent/agents`: Builder, sensitivity, plotting, writers, critic
- `investing_agent/connectors`: EDGAR, Stooq/Yahoo (prices), UST (risk-free)
- `investing_agent/ui`: Report builders and templates (minimalist and interactive)
- `investing_agent/evaluation`: Quality evaluation framework
- `scripts`: CLI tools for report generation and analysis
- `tests`: Comprehensive test suite with quality gates

## Advanced Usage

### Evidence-Enhanced Reports
```bash
# Generate report with evidence pipeline
python scripts/report_with_evidence.py AAPL

# Set evidence confidence threshold
python scripts/report_with_evidence.py AAPL --evidence-threshold 0.85

# Force new research (override frozen evidence)
python scripts/report_with_evidence.py AAPL --force-new-research
```

### Valuation Overrides
```bash
# Override growth rates
python scripts/report.py AAPL --growth '8%,7%,6%'

# Override operating margins
python scripts/report.py AAPL --margin '12%,13%,14%'

# Override sales-to-capital
python scripts/report.py AAPL --s2c '2.0,2.2,2.4'
```

### Configuration Files
```yaml
# config.yaml
horizon: 10
discounting: midyear
beta: 1.1
stable_growth: 0.025
stable_margin: 0.18
growth: ["8%", "7%", "6%", "5%"]
margin: [0.16, 0.17, 0.18]
s2c: [2.0, 2.1, 2.2]
macro:
  risk_free_curve: [0.04, 0.04, 0.04]
  erp: 0.05
  country_risk: 0.0
```

Use with: `python scripts/report.py AAPL --config config.yaml`

## Testing

### Run Tests
```bash
# All tests
pytest -q

# Evaluation tests only
pytest -q -m eval

# Acceptance tests
pytest -q tests/acceptance

# Golden canary tests
pytest -q -k canaries_golden
```

### Quality Gates
- Minimum overall score: 6.0/10
- Dimensional requirements: No dimension below 5.0/10
- Citation density: ≥70% of paragraphs must contain references
- Numeric accuracy: All calculations must match kernel outputs

## Report Artifacts

### Output Directory Structure
```
out/
└── TICKER/
    ├── TICKER_report.html         # Main minimalist HTML report
    ├── report_data.json           # Report data and narratives
    ├── TICKER_evaluation.json     # Quality evaluation scores
    ├── series.csv                 # Per-year financial projections
    ├── fundamentals.csv           # Parsed annual financials
    ├── companyfacts.json          # Raw EDGAR data
    └── evidence/                  # Evidence pipeline artifacts
        ├── frozen_evidence_*.json
        ├── model_pr_log_*.json
        └── snapshots/
```

## API Safety

**IMPORTANT**: Always requires explicit permission before API calls
- Default model: gpt-5-mini (cost: ~$0.0008/report)
- Premium model: gpt-5 (cost: ~$0.15/report)
- Never generate more than 3 reports without confirmation
- See `API_SAFETY_SETTINGS.md` for detailed guidelines

## Contributing

1. Follow the agent design principles in `AGENTS.md`
2. Ensure all changes pass quality gates: `make ci`
3. Update documentation for new features
4. Add tests for new functionality
5. Use the evaluation framework to validate report quality

## License

Proprietary - See LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: https://github.com/anthropics/claude-code/issues
- Documentation: See docs/ directory
- Troubleshooting: See TROUBLESHOOTING.md

---

*Built with a focus on reliability, transparency, and professional-grade investment analysis.*